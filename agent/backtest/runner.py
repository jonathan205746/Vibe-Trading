"""Fixed backtest entrypoint: read config.json, select loader by source, import signal_engine, run engine.

Supports ``source="auto"`` to route codes to loaders by symbol format.
Supports ``interval`` for bar size (1m/5m/15m/30m/1H/4H/1D, default 1D).
Supports ``engine`` for backtest engine (daily/options, default daily).

Usage: ``python -m backtest.runner <run_dir>``
"""

import importlib.util
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backtest.loaders.registry import (
    LOADER_REGISTRY,
    get_loader_cls_with_fallback,
    resolve_loader,
)
from backtest.loaders.base import NoAvailableSourceError

logger = logging.getLogger(__name__)


def _load_module_from_file(file_path: Path, module_name: str):
    """Load a Python module from a file path via importlib.

    Args:
        file_path: Path to the ``.py`` file.
        module_name: Logical module name.

    Returns:
        Loaded module object.
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- Market detection (returns market type, NOT source name) ---

_MARKET_PATTERNS = [
    (re.compile(r"^\d{6}\.(SZ|SH|BJ)$", re.I), "a_share"),
    (re.compile(r"^(51|15|56)\d{4}\.(SZ|SH)$", re.I), "a_share"),
    (re.compile(r"^[A-Z]+\.US$", re.I), "us_equity"),
    (re.compile(r"^\d{3,5}\.HK$", re.I), "hk_equity"),
    (re.compile(r"^[A-Z]+-USDT$", re.I), "crypto"),
    (re.compile(r"^[A-Z]+/USDT$", re.I), "crypto"),
    (re.compile(r"^[A-Z]{1,2}\d{3,4}\.(ZCE|DCE|SHFE|INE|CFFEX|GFEX)$", re.I), "futures"),
    (re.compile(r"^[A-Z]{3}/[A-Z]{3}$"), "forex"),
    (re.compile(r"^[A-Z]{6}\.FX$"), "forex"),
]

# Back-compat: market type -> legacy source name (for engine selection & metrics)
_MARKET_TO_SOURCE = {
    "a_share": "tushare",
    "us_equity": "yfinance",
    "hk_equity": "yfinance",
    "crypto": "okx",
    "futures": "tushare",
    "fund": "tushare",
    "macro": "akshare",
    "forex": "akshare",
}


def _detect_market(code: str) -> str:
    """Infer market type from symbol format.

    Args:
        code: Ticker / symbol string.

    Returns:
        Market type (a_share/us_equity/hk_equity/crypto/futures/forex);
        unknown defaults to ``a_share``.
    """
    for pattern, market in _MARKET_PATTERNS:
        if pattern.match(code):
            return market
    return "a_share"


def _detect_source(code: str) -> str:
    """Infer legacy source name from symbol (back-compat for metrics/engine).

    Args:
        code: Ticker / symbol string.

    Returns:
        Source name (tushare/okx/yfinance/akshare).
    """
    market = _detect_market(code)
    return _MARKET_TO_SOURCE.get(market, "tushare")


def _group_codes_by_market(codes: List[str]) -> Dict[str, List[str]]:
    """Group symbols by detected market type.

    Args:
        codes: List of symbol strings.

    Returns:
        Mapping market_type -> list of codes.
    """
    groups: Dict[str, List[str]] = {}
    for code in codes:
        market = _detect_market(code)
        groups.setdefault(market, []).append(code)
    return groups


def _group_codes_by_source(codes: List[str]) -> Dict[str, List[str]]:
    """Group symbols by inferred source (back-compat).

    Args:
        codes: List of symbol strings.

    Returns:
        Mapping source -> list of codes.
    """
    groups: Dict[str, List[str]] = {}
    for code in codes:
        src = _detect_source(code)
        groups.setdefault(src, []).append(code)
    return groups


def _get_loader(source: str):
    """Return a DataLoader class for a source name, with fallback.

    Args:
        source: Source name (tushare/okx/yfinance/akshare/ccxt).

    Returns:
        DataLoader class.
    """
    try:
        return get_loader_cls_with_fallback(source)
    except NoAvailableSourceError:
        # Ultimate fallback for unknown sources
        if "tushare" in LOADER_REGISTRY:
            return LOADER_REGISTRY["tushare"]
        raise


def _normalize_codes(codes: List[str], source: str) -> List[str]:
    """Normalize symbol strings for a source.

    Args:
        codes: Raw code list.
        source: Data source.

    Returns:
        Normalized codes.
    """
    if source in ("okx", "ccxt"):
        return [c.replace("/", "-").upper() for c in codes]
    return codes


# --- Main entry ---

def main(run_dir: Path) -> None:
    """Load config, fetch data, run the selected backtest engine.

    With ``source="auto"``, routes each code through the appropriate loader.

    Args:
        run_dir: Run directory containing ``config.json`` and ``code/signal_engine.py``.
    """
    config_path = run_dir / "config.json"
    if not config_path.exists():
        print(json.dumps({"error": "config.json not found"}))
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = config.get("source", "tushare")
    codes = config.get("codes", [])

    # Load signal engine
    signal_path = run_dir / "code" / "signal_engine.py"
    if not signal_path.exists():
        print(json.dumps({"error": "code/signal_engine.py not found"}))
        sys.exit(1)

    signal_module = _load_module_from_file(signal_path, "signal_engine")
    engine_cls = getattr(signal_module, "SignalEngine", None)
    if engine_cls is None:
        print(json.dumps({"error": "SignalEngine class not found in signal_engine.py"}))
        sys.exit(1)

    # Data: auto split vs single loader
    interval = config.get("interval", "1D")

    if source == "auto":
        data_map = _fetch_auto(codes, config, interval)
    else:
        codes = _normalize_codes(codes, source)
        config["codes"] = codes
        LoaderCls = _get_loader(source)
        loader = LoaderCls()
        data_map = loader.fetch(
            codes,
            config.get("start_date", ""),
            config.get("end_date", ""),
            fields=config.get("extra_fields") or None,
            interval=interval,
        )
    if not data_map:
        print(json.dumps({"error": "No data fetched"}))
        sys.exit(1)

    # Engine
    engine_type = config.get("engine", "daily")
    signal_engine = engine_cls()

    # Annualization bars
    effective_source = _detect_primary_source(codes, source)
    from backtest.metrics import calc_bars_per_year
    bars_per_year = calc_bars_per_year(interval, effective_source)

    # Auto mode: wrap preloaded data in a dummy loader
    if source == "auto":
        loader = _AutoLoader(data_map)

    if engine_type == "options":
        from backtest.engines.options_portfolio import run_options_backtest
        run_options_backtest(config, loader, signal_engine, run_dir, bars_per_year=bars_per_year)
    else:
        market_engine = _create_market_engine(effective_source, config, codes)
        market_engine.run_backtest(config, loader, signal_engine, run_dir, bars_per_year=bars_per_year)


def _create_market_engine(source: str, config: dict, codes: List[str]):
    """Create the appropriate market engine based on data source.

    Args:
        source: Data source (okx/ccxt/tushare/akshare/yfinance).
        config: Backtest configuration.
        codes: Instrument codes.

    Returns:
        BaseEngine subclass instance.
    """
    if source in ("okx", "ccxt"):
        from backtest.engines.crypto import CryptoEngine
        return CryptoEngine(config)
    elif source in ("tushare", "akshare"):
        # Determine if codes look like A-shares or global equities
        markets = {_detect_market(c) for c in codes}
        if markets & {"us_equity", "hk_equity"}:
            from backtest.engines.global_equity import GlobalEquityEngine
            market = _detect_submarket(codes)
            return GlobalEquityEngine(config, market=market)
        from backtest.engines.china_a import ChinaAEngine
        return ChinaAEngine(config)
    elif source == "yfinance":
        from backtest.engines.global_equity import GlobalEquityEngine
        market = _detect_submarket(codes)
        return GlobalEquityEngine(config, market=market)
    else:
        from backtest.engines.crypto import CryptoEngine
        return CryptoEngine(config)


def _detect_submarket(codes: List[str]) -> str:
    """Detect US vs HK from symbol suffixes.

    Args:
        codes: Instrument codes.

    Returns:
        "hk" if any code ends with .HK, else "us".
    """
    for code in codes:
        if code.upper().endswith(".HK"):
            return "hk"
    return "us"


def _detect_primary_source(codes: List[str], source: str) -> str:
    """Pick primary source for annualization (e.g. bars per year).

    Args:
        codes: All symbols.
        source: Config ``source`` field.

    Returns:
        Dominant source name.
    """
    if source != "auto":
        return source
    groups = _group_codes_by_source(codes)
    if len(groups) == 1:
        return list(groups.keys())[0]
    # Mixed: use the source with the most symbols
    return max(groups, key=lambda s: len(groups[s]))


def _fetch_auto(codes: List[str], config: dict, interval: str = "1D") -> dict:
    """Auto mode: route each market group through fallback chain.

    Args:
        codes: All symbols.
        config: Backtest config dict.
        interval: Bar interval string.

    Returns:
        Merged ``code -> DataFrame`` map.
    """
    market_groups = _group_codes_by_market(codes)
    merged = {}
    start_date = config.get("start_date", "")
    end_date = config.get("end_date", "")

    for market, market_codes in market_groups.items():
        try:
            loader = resolve_loader(market)
        except NoAvailableSourceError as exc:
            # Fallback: try legacy source mapping
            legacy_src = _MARKET_TO_SOURCE.get(market, "tushare")
            logger.warning("Fallback chain failed for %s: %s — trying %s", market, exc, legacy_src)
            LoaderCls = _get_loader(legacy_src)
            loader = LoaderCls()

        src_name = getattr(loader, "name", "unknown")
        normalized_codes = _normalize_codes(market_codes, src_name)
        fields = config.get("extra_fields") if src_name == "tushare" else None
        result = loader.fetch(normalized_codes, start_date, end_date, fields=fields, interval=interval)
        merged.update(result)

    return merged


class _AutoLoader:
    """Dummy loader for auto mode: returns pre-fetched data maps."""

    def __init__(self, data_map: dict):
        self._data = data_map

    def fetch(self, codes, start_date, end_date, fields=None, interval="1D"):
        """Return preloaded rows for requested codes."""
        return {c: df for c, df in self._data.items() if c in codes}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python -m backtest.runner <run_dir>")
        sys.exit(1)
    main(Path(sys.argv[1]))
