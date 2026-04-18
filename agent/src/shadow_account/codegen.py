"""Shadow Account — code generation (rules → signal_engine.py + config.json).

Inputs are always a ``ShadowProfile`` (contract-stable). Outputs are:
    * ``signal_engine.py`` source, validated with ``ast.parse`` + a shape
      check on ``class SignalEngine.generate``.
    * ``config.json`` dict, ready to drop into a run_dir.

No external I/O here — callers (backtester) are responsible for writing
files and launching ``run_backtest``.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.shadow_account.models import ShadowProfile, ShadowRule

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_SIGNAL_ENGINE_TEMPLATE = "signal_engine.py.j2"


def _env() -> Environment:
    """Jinja2 environment rooted at our templates directory."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _rule_to_context(rule: ShadowRule) -> dict[str, Any]:
    """Flatten a ShadowRule into the scalar fields the template consumes."""
    market = str(rule.entry_condition.get("market", "other"))
    hour = rule.entry_condition.get("entry_hour") or {}
    hold_lo, hold_hi = rule.holding_days_range
    hold_days = max(1, int(round((hold_lo + hold_hi) / 2)))
    return {
        "rule_id": rule.rule_id,
        "market": market,
        "entry_hour_min": int(hour.get("min", 0)),
        "entry_hour_max": int(hour.get("max", 23)),
        "hold_days": hold_days,
        "weight": float(rule.weight),
    }


def render_signal_engine(profile: ShadowProfile) -> str:
    """Render the SignalEngine Python source for a profile.

    Args:
        profile: ShadowProfile carrying the rules to replay.

    Returns:
        Python source string. The caller is expected to ``validate_generated``
        before writing to disk.
    """
    template = _env().get_template(_SIGNAL_ENGINE_TEMPLATE)
    return template.render(
        shadow_id=profile.shadow_id,
        profitable_roundtrips=profile.profitable_roundtrips,
        date_range=list(profile.date_range),
        preferred_markets=list(profile.preferred_markets),
        rules=[_rule_to_context(r) for r in profile.rules],
    )


def validate_generated(source: str) -> tuple[bool, str]:
    """Static-check a generated signal_engine source.

    Checks:
        1. ``ast.parse`` succeeds.
        2. Module defines ``class SignalEngine``.
        3. ``SignalEngine`` has a ``generate`` method with one positional
           arg besides self.

    Returns:
        (ok, error_msg). ``error_msg`` is empty on success.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"

    signal_cls: ast.ClassDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SignalEngine":
            signal_cls = node
            break
    if signal_cls is None:
        return False, "class SignalEngine not found"

    generate: ast.FunctionDef | None = None
    for node in signal_cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == "generate":
            generate = node
            break
    if generate is None:
        return False, "SignalEngine.generate method not found"

    non_self_args = [a for a in generate.args.args if a.arg != "self"]
    if len(non_self_args) < 1:
        return False, "SignalEngine.generate must accept a data_map argument"
    return True, ""


def render_config(
    profile: ShadowProfile,
    *,
    codes: list[str],
    start_date: str,
    end_date: str,
    source: str = "auto",
    initial_capital: float = 1_000_000.0,
    interval: str = "1D",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the ``config.json`` dict for a shadow backtest run.

    Args:
        profile: ShadowProfile (used only for metadata, not for engine logic).
        codes: Symbols to backtest across.
        start_date / end_date: ISO dates.
        source: Loader source; ``auto`` routes by symbol suffix.
        initial_capital: Starting cash.
        interval: Bar size (daily default).
        extra: Arbitrary overrides merged last.
    """
    cfg: dict[str, Any] = {
        "source": source,
        "codes": codes,
        "start_date": start_date,
        "end_date": end_date,
        "interval": interval,
        "initial_capital": initial_capital,
        "engine": "daily",
        "shadow_id": profile.shadow_id,
    }
    if extra:
        cfg.update(extra)
    return cfg


def write_run_dir(
    profile: ShadowProfile,
    run_dir: Path,
    *,
    codes: list[str],
    start_date: str,
    end_date: str,
    source: str = "auto",
    initial_capital: float = 1_000_000.0,
) -> Path:
    """Materialize a full run_dir with ``code/signal_engine.py`` + ``config.json``.

    Raises:
        ValueError: Generated signal_engine fails static validation.
    """
    run_dir = Path(run_dir)
    (run_dir / "code").mkdir(parents=True, exist_ok=True)

    source_code = render_signal_engine(profile)
    ok, err = validate_generated(source_code)
    if not ok:
        raise ValueError(f"Generated signal_engine failed validation: {err}")

    (run_dir / "code" / "signal_engine.py").write_text(source_code, encoding="utf-8")
    cfg = render_config(
        profile,
        codes=codes,
        start_date=start_date,
        end_date=end_date,
        source=source,
        initial_capital=initial_capital,
    )
    (run_dir / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return run_dir
