"""Extracted per-bar market hooks as pure functions.

Both the original engines (CryptoEngine, ForexEngine) and CompositeEngine
call these same functions. Zero duplication — one source of truth.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

from backtest.models import Position

# ── Crypto: OKX tiered maintenance margin table (simplified) ──

_TIER_TABLE = [
    (100_000, 0.004),
    (500_000, 0.006),
    (1_000_000, 0.01),
    (5_000_000, 0.02),
    (10_000_000, 0.05),
    (float("inf"), 0.10),
]

FUNDING_HOURS = {0, 8, 16}


def _maintenance_rate(notional_usd: float) -> float:
    """Look up tiered maintenance margin rate."""
    for tier_max, rate in _TIER_TABLE:
        if notional_usd <= tier_max:
            return rate
    return _TIER_TABLE[-1][1]


def calc_crypto_funding_fee(
    symbol: str,
    bar: pd.Series,
    timestamp: pd.Timestamp,
    positions: Dict[str, Position],
    funding_rate: float,
    applied_set: set,
    daily_done_set: set,
) -> float:
    """Calculate crypto funding fee for one symbol.

    Args:
        symbol: Instrument code.
        bar: Current bar data.
        timestamp: Bar timestamp.
        positions: Shared positions dict.
        funding_rate: Fixed rate per settlement.
        applied_set: (symbol, date, hour) dedup set — mutated.
        daily_done_set: (symbol, date) dedup set — mutated.

    Returns:
        Fee amount (positive = longs pay, negative = longs receive).
    """
    if not hasattr(timestamp, "date"):
        return 0.0

    current_date = timestamp.date()
    hour = timestamp.hour if hasattr(timestamp, "hour") else 0

    if hour in FUNDING_HOURS:
        key = (symbol, current_date, hour)
        if key in applied_set:
            return 0.0
        applied_set.add(key)
    else:
        day_key = (symbol, current_date)
        if day_key in daily_done_set:
            return 0.0
        daily_done_set.add(day_key)

    pos = positions.get(symbol)
    if pos is None:
        return 0.0

    mark_price = float(bar.get("close", pos.entry_price))
    notional = pos.size * mark_price
    return notional * funding_rate * pos.direction


def check_crypto_liquidation(
    symbol: str,
    bar: pd.Series,
    positions: Dict[str, Position],
) -> bool:
    """Check if a crypto position should be liquidated.

    Args:
        symbol: Instrument code.
        bar: Current bar data.
        positions: Shared positions dict.

    Returns:
        True if liquidation should be triggered.
        Does NOT execute the liquidation -- caller handles that.
    """
    pos = positions.get(symbol)
    if pos is None or pos.leverage <= 1.0:
        return False

    mark_price = float(bar.get("close", pos.entry_price))
    margin = pos.size * pos.entry_price / pos.leverage
    unrealized = pos.direction * pos.size * (mark_price - pos.entry_price)

    notional = pos.size * mark_price
    maint_rate = _maintenance_rate(notional)
    maint_margin = notional * maint_rate

    return (margin + unrealized) <= maint_margin


# ── Forex: swap tables ──

_SWAP_LONG: dict[str, float] = {
    "EUR/USD": -6.5, "GBP/USD": -3.0, "USD/JPY": 8.0, "USD/CHF": 4.0,
    "AUD/USD": -2.0, "USD/CAD": 2.0, "NZD/USD": -1.5,
}
_SWAP_SHORT: dict[str, float] = {
    "EUR/USD": 3.5, "GBP/USD": -1.0, "USD/JPY": -12.0, "USD/CHF": -8.0,
    "AUD/USD": -1.0, "USD/CAD": -5.0, "NZD/USD": -2.0,
}


def _normalize_symbol(symbol: str) -> str:
    """Normalize forex symbol to 'XXX/YYY' format."""
    s = symbol.replace(".FX", "").replace(".", "").strip()
    if "/" in s:
        return s.upper()
    if len(s) == 6:
        return f"{s[:3]}/{s[3:]}".upper()
    return s.upper()


def calc_forex_swap(
    symbol: str,
    timestamp: pd.Timestamp,
    positions: Dict[str, Position],
    lot_size: float,
    last_swap_dates: dict,
) -> float:
    """Calculate forex swap for one symbol.

    Args:
        symbol: Forex pair.
        timestamp: Bar timestamp.
        positions: Shared positions dict.
        lot_size: Standard lot size (e.g. 100_000).
        last_swap_dates: Per-symbol date tracking dict -- mutated.

    Returns:
        Swap amount (positive = credit, negative = debit).
    """
    if not hasattr(timestamp, "date"):
        return 0.0

    current_date = timestamp.date()
    if last_swap_dates.get(symbol) == current_date:
        return 0.0
    last_swap_dates[symbol] = current_date

    pos = positions.get(symbol)
    if pos is None:
        return 0.0

    pair = _normalize_symbol(symbol)
    lots = pos.size / lot_size

    if pos.direction == 1:
        swap_per_lot = _SWAP_LONG.get(pair, -1.0)
    else:
        swap_per_lot = _SWAP_SHORT.get(pair, -1.0)

    # Wednesday = triple swap (covers Sat+Sun)
    multiplier = 3.0 if timestamp.weekday() == 2 else 1.0
    return lots * swap_per_lot * multiplier
