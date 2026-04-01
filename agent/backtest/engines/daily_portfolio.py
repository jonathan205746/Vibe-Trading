"""Portfolio-level vectorised backtest engine.

Supports arbitrary bar intervals (1m/5m/15m/30m/1H/4H/1D).
Signal lag: bar-T signal executes at bar T+1 (close-to-close return approx).
Position normalisation: sum(abs(weights)) <= 1.0, no leverage ever.
Commission: deducted as percentage of turnover.
Artifacts: equity.csv, metrics.csv, trades.csv, positions.csv, ohlcv_{code}.csv.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd


# ─── Annualisation factor mapping (auto-inferred from source and interval) ───

_TRADING_DAYS = {"tushare": 252, "yfinance": 252, "okx": 365}
_BARS_PER_DAY = {
    "1m":  {"tushare": 240, "okx": 1440, "yfinance": 390},
    "5m":  {"tushare": 48,  "okx": 288,  "yfinance": 78},
    "15m": {"tushare": 16,  "okx": 96,   "yfinance": 26},
    "30m": {"tushare": 8,   "okx": 48,   "yfinance": 13},
    "1H":  {"tushare": 4,   "okx": 24,   "yfinance": 7},
    "4H":  {"tushare": 1,   "okx": 6,    "yfinance": 2},
    "1D":  {"tushare": 1,   "okx": 1,    "yfinance": 1},
}


def _calc_bars_per_year(interval: str = "1D", source: str = "tushare") -> int:
    """Calculate the number of bars per year for annualisation.

    Args:
        interval: Bar interval (e.g. 1m, 1H, 1D).
        source: Data source (determines trading days and bars per day).

    Returns:
        Number of bars per year, used for annualised return and Sharpe ratio.
    """
    trading_days = _TRADING_DAYS.get(source, 252)
    bars_per_day = _BARS_PER_DAY.get(interval, {}).get(source, 1)
    return trading_days * bars_per_day


def _align(
    data_map: Dict[str, pd.DataFrame],
    signal_map: Dict[str, pd.Series],
    codes: List[str],
    optimizer: Optional[Callable] = None,
) -> tuple:
    """Build aligned date index, close matrix, position matrix, and return matrix.

    For multi-market mixes, takes the union of all trading dates and forward-fills gaps.
    Applies signal shift(1), optional optimizer weighting, and normalisation (sum|w|<=1).

    Args:
        data_map: code -> OHLCV DataFrame.
        signal_map: code -> signal Series.
        codes: List of valid instrument codes.
        optimizer: Optional weight optimisation function (ret_df, pos_df, date_idx) -> pos_df.

    Returns:
        (dates, close_df, positions_df, returns_df)
    """
    all_dates = set()
    for c in codes:
        all_dates.update(data_map[c].index)
    dates = pd.DatetimeIndex(sorted(all_dates))

    close = pd.DataFrame(index=dates, columns=codes, dtype=float)
    for c in codes:
        close[c] = data_map[c]["close"].reindex(dates)
    close = close.ffill().bfill()

    pos = pd.DataFrame(0.0, index=dates, columns=codes)
    for c in codes:
        raw = signal_map[c].reindex(dates).fillna(0.0).clip(-1.0, 1.0)
        pos[c] = raw.shift(1).fillna(0.0)

    ret = close.pct_change().fillna(0.0)

    # optimizer weighting (before normalisation)
    if optimizer is not None:
        pos = optimizer(ret, pos, dates)

    scale = pos.abs().sum(axis=1).clip(lower=1.0)
    pos = pos.div(scale, axis=0)

    return dates, close, pos, ret


def _benchmark_equity(
    ret: pd.DataFrame,
    cash: float,
) -> tuple:
    """Calculate equal-weight buy-and-hold benchmark.

    Args:
        ret: Return matrix.
        cash: Initial capital.

    Returns:
        (bench_ret Series, bench_equity Series)
    """
    n_assets = ret.shape[1]
    bench_ret = ret.mean(axis=1) if n_assets > 0 else pd.Series(0.0, index=ret.index)
    bench_equity = cash * (1 + bench_ret).cumprod()
    return bench_ret, bench_equity


def _portfolio_equity(
    pos: pd.DataFrame,
    ret: pd.DataFrame,
    commission: float,
    cash: float,
) -> tuple:
    """Portfolio returns -> equity curve -> drawdown.

    Args:
        pos: Position matrix.
        ret: Return matrix.
        commission: Commission rate.
        cash: Initial capital.

    Returns:
        (port_ret Series, equity Series, drawdown Series)
    """
    port_ret = (pos * ret).sum(axis=1)
    turnover = pos.diff().abs().sum(axis=1).fillna(0.0)
    port_ret = port_ret - turnover * commission
    equity = cash * (1 + port_ret).cumprod()
    peak = equity.cummax()
    dd = (equity - peak) / peak.replace(0, 1)
    return port_ret, equity, dd


def _log_trades(
    pos: pd.DataFrame,
    close: pd.DataFrame,
    codes: List[str],
) -> List[Dict[str, Any]]:
    """Generate per-trade records from position diffs, including per-trade P&L.

    Args:
        pos: Position matrix.
        close: Close price matrix.
        codes: List of instrument codes.

    Returns:
        Trade list sorted by timestamp.
    """
    diff = pos.diff()
    diff.iloc[0] = pos.iloc[0]

    # Track entry cost and entry date per instrument
    cost: Dict[str, float] = {}
    hold: Dict[str, float] = {}
    entry_date: Dict[str, str] = {}

    trades: List[Dict[str, Any]] = []
    # Collect all trade events then sort by timestamp
    raw_events = []
    for c in codes:
        delta = diff[c]
        for ts in delta.index[delta.abs() > 1e-9]:
            d = float(delta.loc[ts])
            p = float(close.at[ts, c]) if pd.notna(close.at[ts, c]) else 0.0
            raw_events.append((str(ts.date()) if hasattr(ts, "date") else str(ts), c, d, p))
    raw_events.sort(key=lambda x: x[0])

    for ts_str, c, d, p in raw_events:
        side = "buy" if d > 0 else "sell"
        qty = abs(d)
        pnl = 0.0
        holding_days = 0
        return_pct = 0.0

        prev = hold.get(c, 0.0)
        if prev * d >= 0:
            # Same-direction add: update average cost
            old = cost.get(c, p)
            total = abs(prev) + qty
            cost[c] = (old * abs(prev) + p * qty) / total if total > 1e-9 else p
            hold[c] = prev + d
            if c not in entry_date:
                entry_date[c] = ts_str
        else:
            # Opposite direction: realise P&L
            close_qty = min(qty, abs(prev))
            entry = cost.get(c, p)
            pnl = (p - entry) * close_qty if prev > 0 else (entry - p) * close_qty
            return_pct = (p / entry - 1) * 100 if entry > 1e-9 and prev > 0 else (entry / p - 1) * 100 if p > 1e-9 else 0.0

            ed = entry_date.get(c, ts_str)
            try:
                holding_days = (pd.Timestamp(ts_str) - pd.Timestamp(ed)).days
            except Exception:
                holding_days = 0

            remain = prev + d
            if abs(remain) < 1e-9:
                hold.pop(c, None)
                cost.pop(c, None)
                entry_date.pop(c, None)
            else:
                hold[c] = remain
                if remain * prev <= 0:
                    cost[c] = p
                    entry_date[c] = ts_str

        trades.append({
            "timestamp": ts_str,
            "code": c,
            "side": side,
            "price": round(p, 4),
            "qty": round(qty, 6),
            "reason": "signal",
            "pnl": round(pnl, 4),
            "holding_days": holding_days,
            "return_pct": round(return_pct, 2),
        })

    return trades


def _win_rate_and_stats(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate win rate and P&L statistics from trade records.

    Args:
        trades: List of trade records.

    Returns:
        Dict containing win_rate, profit_loss_ratio, max_consecutive_loss, avg_holding_days.
    """
    closed = [t for t in trades if t.get("pnl", 0) != 0]
    if not closed:
        return {"win_rate": 0.0, "profit_loss_ratio": 0.0, "max_consecutive_loss": 0, "avg_holding_days": 0.0}

    wins = [t["pnl"] for t in closed if t["pnl"] > 0]
    losses = [t["pnl"] for t in closed if t["pnl"] < 0]
    win_rate = len(wins) / len(closed) if closed else 0.0

    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = abs(np.mean(losses)) if losses else 1e-10
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 1e-10 else 0.0

    # Max consecutive losses
    max_consec = 0
    cur_consec = 0
    for t in closed:
        if t["pnl"] < 0:
            cur_consec += 1
            max_consec = max(max_consec, cur_consec)
        else:
            cur_consec = 0

    # Average holding days
    hold_days = [t["holding_days"] for t in closed if t["holding_days"] > 0]
    avg_holding = np.mean(hold_days) if hold_days else 0.0

    return {
        "win_rate": win_rate,
        "profit_loss_ratio": round(profit_loss_ratio, 4),
        "max_consecutive_loss": max_consec,
        "avg_holding_days": round(avg_holding, 1),
    }


def _metrics(
    port_ret: pd.Series,
    equity: pd.Series,
    dd: pd.Series,
    cash: float,
    trades: List[Dict[str, Any]],
    bench_ret: Optional[pd.Series] = None,
    bars_per_year: int = 252,
) -> Dict[str, Any]:
    """Calculate the full set of performance metrics.

    Args:
        port_ret: Portfolio bar return series.
        equity: Equity curve.
        dd: Drawdown series.
        cash: Initial capital.
        trades: Trade records.
        bench_ret: Benchmark return series (optional).
        bars_per_year: Bars per year (252 for daily, 8760 for 1H OKX, etc.).

    Returns:
        Metrics dictionary.
    """
    n = len(port_ret)
    if n == 0:
        return dict(
            final_value=cash, total_return=0, annual_return=0,
            max_drawdown=0, sharpe=0, calmar=0, sortino=0,
            win_rate=0, profit_loss_ratio=0, max_consecutive_loss=0,
            avg_holding_days=0, trade_count=0,
            benchmark_return=0, excess_return=0, information_ratio=0,
        )

    bpy = bars_per_year

    total_ret = float(equity.iloc[-1] / cash - 1)
    ann_ret = float((1 + total_ret) ** (bpy / max(n, 1)) - 1)
    vol = float(port_ret.std())
    sharpe = float(port_ret.mean() / (vol + 1e-10) * np.sqrt(bpy))

    # Calmar = annualised return / |max drawdown|
    max_dd = float(dd.min())
    calmar = ann_ret / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    # Sortino = mean(ret) / downside_std * sqrt(bars_per_year)  (unchanged)
    downside = port_ret[port_ret < 0]
    downside_std = float(downside.std()) if len(downside) > 1 else 1e-10
    sortino = float(port_ret.mean() / (downside_std + 1e-10) * np.sqrt(bpy))

    # Trade statistics
    trade_stats = _win_rate_and_stats(trades)

    # Benchmark comparison
    bench_return = 0.0
    excess = 0.0
    ir = 0.0
    if bench_ret is not None and len(bench_ret) > 0:
        bench_return = float((1 + bench_ret).prod() - 1)
        excess = total_ret - bench_return
        active_ret = port_ret - bench_ret
        active_std = float(active_ret.std())
        ir = float(active_ret.mean() / (active_std + 1e-10) * np.sqrt(bpy))

    return {
        "final_value": float(equity.iloc[-1]),
        "total_return": total_ret,
        "annual_return": ann_ret,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "calmar": round(calmar, 4),
        "sortino": round(sortino, 4),
        "win_rate": trade_stats["win_rate"],
        "profit_loss_ratio": trade_stats["profit_loss_ratio"],
        "max_consecutive_loss": trade_stats["max_consecutive_loss"],
        "avg_holding_days": trade_stats["avg_holding_days"],
        "trade_count": len(trades),
        "benchmark_return": round(bench_return, 6),
        "excess_return": round(excess, 6),
        "information_ratio": round(ir, 4),
    }


def run_backtest(
    config: Dict[str, Any],
    loader: Any,
    engine: Any,
    run_dir: Path,
    bars_per_year: int = 252,
) -> Dict[str, Any]:
    """Main entry point: load data -> generate signals -> vectorised backtest -> write artifacts.

    Args:
        config: Backtest configuration (codes, start_date, end_date, initial_cash, commission,
                extra_fields, optimizer, interval, source).
        loader: DataLoader instance (must have a fetch method).
        engine: SignalEngine instance (must have a generate method).
        run_dir: Run directory path.
        bars_per_year: Bars per year, computed by runner from interval+source.

    Returns:
        Metrics dictionary.

    Raises:
        SystemExit: When no data is fetched or no valid signals are generated.
    """
    import json
    import sys

    codes = config.get("codes", [])
    start_date = config.get("start_date", "")
    end_date = config.get("end_date", "")
    initial_cash = config.get("initial_cash", 1_000_000)
    commission = config.get("commission", 0.001)
    extra_fields = config.get("extra_fields") or None

    interval = config.get("interval", "1D")
    data_map = loader.fetch(codes, start_date, end_date, fields=extra_fields, interval=interval)
    if not data_map:
        print(json.dumps({"error": "No data fetched"}))
        sys.exit(1)

    signal_map = engine.generate(data_map)
    valid_codes = sorted(c for c in signal_map if c in data_map)
    if not valid_codes:
        print(json.dumps({"error": "No valid signals generated"}))
        sys.exit(1)

    # Load optimizer if configured
    opt_fn = _load_optimizer(config)

    dates, close, pos, ret = _align(data_map, signal_map, valid_codes, optimizer=opt_fn)
    port_ret, equity, dd = _portfolio_equity(pos, ret, commission, initial_cash)
    bench_ret, bench_equity = _benchmark_equity(ret, initial_cash)
    trades = _log_trades(pos, close, valid_codes)
    m = _metrics(port_ret, equity, dd, initial_cash, trades, bench_ret, bars_per_year)

    out = run_dir / "artifacts"
    out.mkdir(parents=True, exist_ok=True)

    for code, df in data_map.items():
        df.to_csv(out / f"ohlcv_{code}.csv")

    eq = pd.DataFrame({
        "ret": port_ret,
        "equity": equity,
        "drawdown": dd,
        "benchmark_equity": bench_equity,
        "active_ret": port_ret - bench_ret,
    }, index=dates)
    eq.index.name = "timestamp"
    eq.to_csv(out / "equity.csv")

    pos.index.name = "timestamp"
    pos.to_csv(out / "positions.csv")

    trade_cols = ["timestamp", "code", "side", "price", "qty", "reason", "pnl", "holding_days", "return_pct"]
    pd.DataFrame(
        trades or [],
        columns=trade_cols,
    ).to_csv(out / "trades.csv", index=False)

    pd.DataFrame([m]).to_csv(out / "metrics.csv", index=False)
    print(json.dumps(m, indent=2))
    return m


def _load_optimizer(config: Dict[str, Any]) -> Optional[Callable]:
    """Dynamically load an optimizer function from config.

    Supports any module under backtest/optimizers/ that exposes an
    `optimize(ret, pos, dates, **params)` function.

    Args:
        config: Backtest configuration.

    Returns:
        Optimizer callable, or None.
    """
    import importlib

    opt_name = config.get("optimizer")
    if not opt_name:
        return None

    opt_params = config.get("optimizer_params") or {}

    try:
        mod = importlib.import_module(f"backtest.optimizers.{opt_name}")
        return lambda ret, pos, dates: mod.optimize(ret, pos, dates, **opt_params)
    except (ImportError, AttributeError) as e:
        print(f"[WARN] Failed to load optimizer '{opt_name}': {e}, falling back to equal weight")
        return None
