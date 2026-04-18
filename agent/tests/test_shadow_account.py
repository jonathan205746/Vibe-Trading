"""Tests for src.shadow_account (Phase 4c — M1).

Fixtures are synthesized in-test via tmp_path; no binary fixtures on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.filterwarnings(
    "ignore:Number of distinct clusters.*:UserWarning",
)

from src.shadow_account import (
    AttributionBreakdown,
    ShadowBacktestResult,
    ShadowProfile,
    ShadowRule,
    extract_shadow_profile,
    find_by_journal_hash,
    load_profile,
    render_config,
    render_shadow_report,
    render_signal_engine,
    run_shadow_backtest,
    save_profile,
    select_multi_market_codes,
    validate_generated,
    write_run_dir,
)
from src.shadow_account.models import AttributionBreakdown as _AttrCls
from src.shadow_account.extractor import MIN_PROFITABLE_ROUNDTRIPS


# ---------------- Helpers ----------------

def _write_journal(path: Path, rows: list[dict]) -> Path:
    """Write a plain-utf8 Tonghuashun-style CSV the parser can ingest."""
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False, encoding="utf-8")
    return path


def _make_tonghuashun_rows(trades: list[tuple[str, str, str, float, float]]) -> list[dict]:
    """Build Tonghuashun-format rows from (datetime, symbol, side, qty, price).

    Tonghuashun requires columns: 成交时间 / 证券代码 / 操作 (see
    `trade_journal_parsers.parse_tonghuashun`).
    """
    out: list[dict] = []
    for dt_str, symbol, side, qty, price in trades:
        amount = qty * price
        out.append({
            "成交时间": dt_str,
            "证券代码": symbol,
            "证券名称": f"标的{symbol}",
            "操作": "买入" if side == "buy" else "卖出",
            "成交数量": qty,
            "成交价格": price,
            "成交金额": round(amount, 2),
            "手续费": round(amount * 0.00025, 2),
            "印花税": round(amount * 0.001, 2) if side == "sell" else 0.0,
            "过户费": 0.0,
        })
    return out


# ---------------- Fixtures ----------------

@pytest.fixture
def profitable_journal(tmp_path: Path) -> Path:
    """15 roundtrips across 5 symbols, all profitable (2% gain each)."""
    trades: list[tuple[str, str, str, float, float]] = []
    symbols = ["600519", "000001", "300750", "600036", "000858"]
    start_day = 1
    for sym in symbols:
        for i in range(3):
            buy_day = start_day + i * 4
            sell_day = buy_day + 2
            trades.append((f"2026-01-{buy_day:02d} 10:30:00", sym, "buy", 100.0, 10.0))
            trades.append((f"2026-01-{sell_day:02d} 14:15:00", sym, "sell", 100.0, 10.2))
    return _write_journal(tmp_path / "journal_profitable.csv", _make_tonghuashun_rows(trades))


@pytest.fixture
def insufficient_journal(tmp_path: Path) -> Path:
    """Only 2 profitable roundtrips — below MIN_PROFITABLE_ROUNDTRIPS."""
    trades = [
        ("2026-01-02 10:30:00", "600519", "buy", 100.0, 10.0),
        ("2026-01-04 14:15:00", "600519", "sell", 100.0, 10.5),
        ("2026-01-06 10:30:00", "000001", "buy", 100.0, 20.0),
        ("2026-01-08 14:15:00", "000001", "sell", 100.0, 20.5),
    ]
    return _write_journal(tmp_path / "journal_few.csv", _make_tonghuashun_rows(trades))


@pytest.fixture
def no_roundtrips_journal(tmp_path: Path) -> Path:
    """Only buys, no sells — zero roundtrips."""
    trades = [
        ("2026-01-02 10:30:00", "600519", "buy", 100.0, 10.0),
        ("2026-01-04 10:30:00", "000001", "buy", 50.0, 20.0),
    ]
    return _write_journal(tmp_path / "journal_nort.csv", _make_tonghuashun_rows(trades))


# ---------------- extract_shadow_profile ----------------

@pytest.mark.unit
def test_extract_profile_happy_path(profitable_journal: Path) -> None:
    profile = extract_shadow_profile(profitable_journal)
    assert isinstance(profile, ShadowProfile)
    assert profile.profitable_roundtrips >= MIN_PROFITABLE_ROUNDTRIPS
    assert profile.total_roundtrips == profile.profitable_roundtrips  # all profitable
    assert profile.source_market == "china_a"
    assert profile.shadow_id.startswith("shadow_")
    assert profile.journal_hash and len(profile.journal_hash) == 40
    assert profile.typical_holding_days[0] > 0
    assert profile.profile_text  # non-empty portrait


@pytest.mark.unit
def test_extract_profile_yields_rules(profitable_journal: Path) -> None:
    from src.shadow_account.extractor import RULE_TEXT_MAX

    profile = extract_shadow_profile(profitable_journal, min_support=2, max_rules=5)
    assert 1 <= len(profile.rules) <= 5
    for rule in profile.rules:
        assert isinstance(rule, ShadowRule)
        assert rule.rule_id.startswith("R")
        assert rule.human_text  # non-empty natural language
        assert len(rule.human_text) <= RULE_TEXT_MAX
        assert rule.human_text.isascii(), f"rule text must be English-only: {rule.human_text!r}"
        assert rule.support_count >= 2
        assert 0.0 < rule.coverage_rate <= 1.0
        lo, hi = rule.holding_days_range
        assert lo >= 1 and hi >= lo


@pytest.mark.unit
def test_extract_profile_rejects_insufficient_sample(insufficient_journal: Path) -> None:
    with pytest.raises(ValueError, match="Insufficient profitable roundtrips"):
        extract_shadow_profile(insufficient_journal)


@pytest.mark.unit
def test_extract_profile_rejects_no_roundtrips(no_roundtrips_journal: Path) -> None:
    with pytest.raises(ValueError, match="No complete buy"):
        extract_shadow_profile(no_roundtrips_journal)


@pytest.mark.unit
def test_extract_profile_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_shadow_profile(tmp_path / "does_not_exist.csv")


@pytest.mark.unit
def test_custom_llm_translator_is_used(profitable_journal: Path) -> None:
    calls: list[dict] = []

    def fake_translator(ctx: dict) -> str:
        calls.append(ctx)
        return "Custom shadow rule text"

    profile = extract_shadow_profile(profitable_journal, llm_translator=fake_translator)
    assert calls, "translator should be invoked at least once"
    assert all(rule.human_text == "Custom shadow rule text" for rule in profile.rules)


# ---------------- Storage round-trip ----------------

@pytest.mark.unit
def test_profile_roundtrip_persistence(
    profitable_journal: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
    profile = extract_shadow_profile(profitable_journal)

    saved_path = save_profile(profile)
    assert saved_path.exists()

    loaded = load_profile(profile.shadow_id)
    assert loaded.shadow_id == profile.shadow_id
    assert loaded.journal_hash == profile.journal_hash
    assert len(loaded.rules) == len(profile.rules)
    assert loaded.rules[0].rule_id == profile.rules[0].rule_id
    assert loaded.preferred_markets == profile.preferred_markets


@pytest.mark.unit
def test_find_by_journal_hash_returns_latest(
    profitable_journal: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    first = extract_shadow_profile(profitable_journal)
    save_profile(first)

    found = find_by_journal_hash(first.journal_hash)
    assert found is not None
    assert found.shadow_id == first.shadow_id
    assert find_by_journal_hash("nonexistent-hash") is None


# ---------------- M2: Codegen ----------------

@pytest.mark.unit
def test_render_signal_engine_produces_valid_python(profitable_journal: Path) -> None:
    profile = extract_shadow_profile(profitable_journal)
    source = render_signal_engine(profile)

    ok, err = validate_generated(source)
    assert ok, f"generated source failed validation: {err}"
    assert "class SignalEngine" in source
    assert profile.shadow_id in source
    assert "def generate" in source


@pytest.mark.unit
def test_validate_generated_rejects_missing_class() -> None:
    ok, err = validate_generated("x = 1\n")
    assert not ok
    assert "SignalEngine" in err


@pytest.mark.unit
def test_validate_generated_rejects_syntax_error() -> None:
    ok, err = validate_generated("class SignalEngine\n  def generate(self, d): pass\n")
    assert not ok
    assert "SyntaxError" in err


@pytest.mark.unit
def test_generated_engine_runs_on_mock_data_map(profitable_journal: Path) -> None:
    """The rendered engine must execute cleanly against a minimal data_map."""
    import importlib.util

    profile = extract_shadow_profile(profitable_journal)
    source = render_signal_engine(profile)

    module_path = Path("./_shadow_test_engine.py").resolve()
    # Use tmp via test's temp dir proxy — write + exec.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "signal_engine.py"
        path.write_text(source, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("gen_signal_engine", path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        engine = module.SignalEngine()

        idx = pd.date_range("2026-01-02", periods=30, freq="B")
        data_map = {
            "600519.SH": pd.DataFrame({"close": range(30)}, index=idx),
            "AAPL": pd.DataFrame({"close": range(30)}, index=idx),
        }
        signals = engine.generate(data_map)
        assert set(signals.keys()) == set(data_map.keys())
        for code, series in signals.items():
            assert isinstance(series, pd.Series)
            assert len(series) == len(idx)
            assert (series >= 0).all()


@pytest.mark.unit
def test_render_config_shape(profitable_journal: Path) -> None:
    profile = extract_shadow_profile(profitable_journal)
    cfg = render_config(
        profile,
        codes=["600519.SH", "AAPL"],
        start_date="2026-01-01",
        end_date="2026-06-30",
    )
    assert cfg["source"] == "auto"
    assert cfg["engine"] == "daily"
    assert cfg["codes"] == ["600519.SH", "AAPL"]
    assert cfg["shadow_id"] == profile.shadow_id


@pytest.mark.unit
def test_write_run_dir_materializes_files(
    profitable_journal: Path, tmp_path: Path,
) -> None:
    profile = extract_shadow_profile(profitable_journal)
    run_dir = write_run_dir(
        profile,
        tmp_path / "run",
        codes=["600519.SH"],
        start_date="2026-01-01",
        end_date="2026-06-30",
    )
    assert (run_dir / "code" / "signal_engine.py").exists()
    assert (run_dir / "config.json").exists()
    cfg = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert cfg["shadow_id"] == profile.shadow_id


# ---------------- M3: Backtester + Attribution ----------------

@pytest.mark.unit
def test_select_multi_market_codes_covers_all_markets(profitable_journal: Path) -> None:
    profile = extract_shadow_profile(profitable_journal)
    selection = select_multi_market_codes(profile, per_market_count=3)
    assert set(selection.keys()) == {"china_a", "hk", "us", "crypto"}
    for market, codes in selection.items():
        assert 1 <= len(codes) <= 3
        assert all(codes)


@pytest.mark.unit
def test_run_shadow_backtest_with_mocked_runner(
    profitable_journal: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inject a stub run_backtest_fn that writes artifacts the parser can read."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    profile = extract_shadow_profile(profitable_journal)

    def stub_run_backtest(run_dir_str: str) -> str:
        run_path = Path(run_dir_str)
        artifacts_dir = run_path / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        metrics_path = artifacts_dir / "metrics.json"
        metrics_path.write_text(json.dumps({
            "total_return_abs": 12_345.0,
            "sharpe": 1.5,
            "max_drawdown": -0.12,
            "win_rate": 0.55,
        }), encoding="utf-8")
        equity_path = artifacts_dir / "equity.csv"
        equity_path.write_text(
            "date,equity\n2026-01-02,1000000\n2026-06-30,1012345\n",
            encoding="utf-8",
        )
        return json.dumps({
            "status": "ok",
            "exit_code": 0,
            "artifacts": {
                "metrics.json": str(metrics_path),
                "equity.csv": str(equity_path),
            },
        })

    result = run_shadow_backtest(
        profile,
        window_start="2026-01-01",
        window_end="2026-06-30",
        journal_path=profitable_journal,
        run_backtest_fn=stub_run_backtest,
    )
    assert isinstance(result, ShadowBacktestResult)
    assert result.shadow_id == profile.shadow_id
    assert set(result.per_market.keys()) == {"china_a", "hk", "us", "crypto"}
    assert result.combined["total_return_abs"] == 12_345.0
    assert result.combined["sharpe"] == 1.5
    assert result.shadow_total_pnl == 12_345.0
    assert result.real_total_pnl > 0  # all profitable test data
    assert result.delta_pnl == round(result.shadow_total_pnl - result.real_total_pnl, 2)
    assert isinstance(result.attribution, AttributionBreakdown)
    assert len(result.equity_curves["combined"]) == 2


@pytest.mark.unit
def test_run_shadow_backtest_handles_runner_failure(
    profitable_journal: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    profile = extract_shadow_profile(profitable_journal)

    def failing_runner(run_dir_str: str) -> str:
        return json.dumps({
            "status": "error",
            "exit_code": 1,
            "stderr": "No data fetched",
            "artifacts": {},
        })

    result = run_shadow_backtest(
        profile,
        window_start="2026-01-01",
        window_end="2026-06-30",
        run_backtest_fn=failing_runner,
    )
    assert result.combined.get("error")
    assert result.shadow_total_pnl == 0.0
    assert result.equity_curves == {}


# ---------------- M4: Reporter ----------------

def _stub_backtest_result(profile: ShadowProfile) -> ShadowBacktestResult:
    return ShadowBacktestResult(
        shadow_id=profile.shadow_id,
        per_market={
            "china_a": {"sharpe": 1.2, "annual_return": 0.15, "max_drawdown": -0.08},
            "us": {"sharpe": 0.9, "annual_return": 0.11, "max_drawdown": -0.10},
        },
        combined={"sharpe": 1.05, "annual_return": 0.13, "max_drawdown": -0.09},
        equity_curves={"combined": [("2026-01-02", 1_000_000.0), ("2026-06-30", 1_130_000.0)]},
        attribution=AttributionBreakdown(
            missed_signals_pnl=50.0,
            noise_trades_pnl=-120.0,
            early_exit_pnl=80.0,
            late_exit_pnl=-20.0,
            overtrading_pnl=10.0,
            counterfactual_trades=(
                {
                    "symbol": "600519.SH", "buy_dt": "2026-02-01", "sell_dt": "2026-02-02",
                    "hold_days": 1.0, "pnl": 100.0, "impact": 50.0, "reason": "early_exit",
                },
            ),
        ),
        shadow_total_pnl=1500.0,
        real_total_pnl=1200.0,
        delta_pnl=300.0,
    )


@pytest.mark.unit
def test_render_shadow_report_emits_html(profitable_journal: Path, tmp_path: Path) -> None:
    profile = extract_shadow_profile(profitable_journal)
    result = _stub_backtest_result(profile)

    out = render_shadow_report(profile, result, output_dir=tmp_path)
    html_path = Path(out["html_path"])
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    assert "Shadow Account" in content
    assert profile.shadow_id in content
    assert "Delta Attribution" in content  # Section 5
    assert "Counterfactual" in content      # Section 6
    assert out["engine"] in ("weasyprint", "html-only")


@pytest.mark.unit
def test_render_shadow_report_includes_today_signals(
    profitable_journal: Path, tmp_path: Path,
) -> None:
    profile = extract_shadow_profile(profitable_journal)
    result = _stub_backtest_result(profile)
    signals = [
        {"symbol": "NVDA", "market": "us", "rule_id": "R1", "reason": "匹配影子规则"},
    ]
    out = render_shadow_report(profile, result, today_signals=signals, output_dir=tmp_path)
    content = Path(out["html_path"]).read_text(encoding="utf-8")
    assert "NVDA" in content
    assert out["sections"]["today_signals"] == signals


@pytest.mark.unit
def test_render_shadow_report_handles_empty_equity(
    profitable_journal: Path, tmp_path: Path,
) -> None:
    profile = extract_shadow_profile(profitable_journal)
    result = ShadowBacktestResult(
        shadow_id=profile.shadow_id,
        per_market={}, combined={}, equity_curves={},
        attribution=AttributionBreakdown(
            missed_signals_pnl=0.0, noise_trades_pnl=0.0, early_exit_pnl=0.0,
            late_exit_pnl=0.0, overtrading_pnl=0.0, counterfactual_trades=(),
        ),
        shadow_total_pnl=0.0, real_total_pnl=0.0, delta_pnl=0.0,
    )
    out = render_shadow_report(profile, result, output_dir=tmp_path)
    assert Path(out["html_path"]).exists()
    # Section 6 should degrade gracefully when no counterfactuals exist.
    assert "No material counterfactual" in Path(out["html_path"]).read_text(encoding="utf-8")


# ---------------- M5/M6: Tool wrappers + scanner ----------------

@pytest.mark.unit
def test_shadow_tools_are_auto_discovered() -> None:
    from src.tools import build_registry

    registry = build_registry()
    for expected in (
        "extract_shadow_strategy",
        "run_shadow_backtest",
        "render_shadow_report",
        "scan_shadow_signals",
    ):
        assert expected in registry.tool_names, f"{expected} missing from registry"


@pytest.mark.unit
def test_extract_shadow_strategy_tool(
    profitable_journal: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.tools.shadow_account_tool import ExtractShadowStrategyTool

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    tool = ExtractShadowStrategyTool()
    out = json.loads(tool.execute(journal_path=str(profitable_journal)))
    assert out["status"] == "ok"
    assert out["shadow_id"].startswith("shadow_")
    assert len(out["rules"]) >= 1
    from src.shadow_account.extractor import RULE_TEXT_MAX
    assert 1 <= len(out["rules"][0]["human_text"]) <= RULE_TEXT_MAX

    # Persistence happened — we can load it back.
    loaded = load_profile(out["shadow_id"])
    assert loaded.shadow_id == out["shadow_id"]


@pytest.mark.unit
def test_extract_shadow_strategy_tool_reports_errors(tmp_path: Path) -> None:
    from src.tools.shadow_account_tool import ExtractShadowStrategyTool

    tool = ExtractShadowStrategyTool()
    out = json.loads(tool.execute(journal_path=str(tmp_path / "missing.csv")))
    assert out["status"] == "error"
    assert "error" in out


@pytest.mark.unit
def test_scan_shadow_signals_tool(
    profitable_journal: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.tools.shadow_account_tool import ScanShadowSignalsTool

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    profile = extract_shadow_profile(profitable_journal)
    save_profile(profile)
    tool = ScanShadowSignalsTool()
    out = json.loads(tool.execute(shadow_id=profile.shadow_id, date="2026-04-18"))
    assert out["status"] == "ok"
    assert out["disclaimer"]
    assert isinstance(out["matches"], list)


@pytest.mark.unit
def test_run_shadow_backtest_tool_handles_missing_id() -> None:
    from src.tools.shadow_account_tool import RunShadowBacktestTool

    out = json.loads(RunShadowBacktestTool().execute(shadow_id="shadow_unknown"))
    assert out["status"] == "error"


@pytest.mark.unit
def test_shadow_account_skill_shipped() -> None:
    skill = Path(__file__).resolve().parents[1] / "src" / "skills" / "shadow-account" / "SKILL.md"
    assert skill.exists()
    body = skill.read_text(encoding="utf-8")
    for needle in ("shadow-account", "extract_shadow_strategy", "run_shadow_backtest", "render_shadow_report", "scan_shadow_signals"):
        assert needle in body, f"skill missing reference to {needle}"


@pytest.mark.unit
def test_context_prompt_references_shadow_account() -> None:
    from src.agent.context import _SYSTEM_PROMPT  # noqa: SLF001 — intentional peek

    assert "Shadow Account" in _SYSTEM_PROMPT
    assert "extract_shadow_strategy" in _SYSTEM_PROMPT
    assert "Phase 4b" not in _SYSTEM_PROMPT  # stale note should be gone


@pytest.mark.unit
def test_attribution_is_zero_without_journal(
    profitable_journal: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    profile = extract_shadow_profile(profitable_journal)

    def stub_runner(run_dir_str: str) -> str:
        metrics_path = Path(run_dir_str) / "metrics.json"
        metrics_path.write_text(json.dumps({"total_return_abs": 0.0}), encoding="utf-8")
        return json.dumps({
            "status": "ok",
            "exit_code": 0,
            "artifacts": {"metrics.json": str(metrics_path)},
        })

    result = run_shadow_backtest(
        profile,
        window_start="2026-01-01",
        window_end="2026-06-30",
        journal_path=None,  # disable attribution
        run_backtest_fn=stub_runner,
    )
    assert result.attribution.noise_trades_pnl == 0.0
    assert result.real_total_pnl == 0.0
    assert result.attribution.counterfactual_trades == ()
