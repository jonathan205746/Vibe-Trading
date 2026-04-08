"""Crypto perpetual-contract backtest engine.

Market rules:
  - 24/7 trading, no restrictions on direction
  - Maker/Taker fee separation
  - Funding fee settlement every 8 hours (00:00/08:00/16:00 UTC)
  - Forced liquidation when maintenance margin ratio <= 100%
  - Fractional position sizes allowed
"""

from __future__ import annotations

import pandas as pd

from backtest.engines.base import BaseEngine


# OKX tiered maintenance margin table (simplified)
# (max_notional_usd, maintenance_margin_rate)
_TIER_TABLE = [
    (100_000, 0.004),
    (500_000, 0.006),
    (1_000_000, 0.01),
    (5_000_000, 0.02),
    (10_000_000, 0.05),
    (float("inf"), 0.10),
]

# Funding fee settlement hours (UTC)
_FUNDING_HOURS = {0, 8, 16}


class CryptoEngine(BaseEngine):
    """Crypto perpetual contract engine.

    Config keys:
      - leverage: default 1.0
      - maker_rate: default 0.0002
      - taker_rate: default 0.0005
      - slippage: default 0.0005
      - margin_mode: "isolated" (default) or "cross"
      - funding_rate: fixed rate per settlement, default 0.0001
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.maker_rate: float = config.get("maker_rate", 0.0002)
        self.taker_rate: float = config.get("taker_rate", 0.0005)
        self.slippage_rate: float = config.get("slippage", 0.0005)
        self.funding_rate: float = config.get("funding_rate", 0.0001)
        self._last_funding_hour: int = -1

    def can_execute(self, symbol: str, direction: int, bar: pd.Series) -> bool:
        """Crypto: 24/7, long/short/close all allowed."""
        return True

    def round_size(self, raw_size: float, price: float) -> float:
        """Crypto supports fractional sizes, round to 6 decimals."""
        return round(max(raw_size, 0.0), 6)

    def calc_commission(self, size: float, price: float, direction: int, is_open: bool) -> float:
        """Maker/Taker separated. Opens typically hit taker, closes hit maker."""
        rate = self.taker_rate if is_open else self.maker_rate
        return size * price * rate

    def apply_slippage(self, price: float, direction: int) -> float:
        """Slippage: unfavourable direction."""
        return price * (1 + direction * self.slippage_rate)

    def on_bar(self, symbol: str, bar: pd.Series, timestamp: pd.Timestamp) -> None:
        """Crypto per-bar hooks: funding fee + liquidation check."""
        self._apply_funding_fee(symbol, bar, timestamp)
        self._check_liquidation(symbol, bar, timestamp)

    # ── Funding fee (exchange-enforced, every 8h) ──

    def _apply_funding_fee(
        self, symbol: str, bar: pd.Series, timestamp: pd.Timestamp,
    ) -> None:
        """Deduct/credit funding fee at settlement hours.

        Positive rate: longs pay shorts. Negative rate: shorts pay longs.
        """
        if not hasattr(timestamp, "hour"):
            return
        hour = timestamp.hour
        if hour not in _FUNDING_HOURS:
            return
        # Avoid double-settlement on same hour
        if hour == self._last_funding_hour:
            return
        self._last_funding_hour = hour

        pos = self.positions.get(symbol)
        if pos is None:
            return

        mark_price = float(bar.get("close", pos.entry_price))
        notional = pos.size * mark_price
        fee = notional * self.funding_rate * pos.direction  # long pays when rate > 0
        self.capital -= fee

    # ── Liquidation (exchange-enforced) ──

    def _check_liquidation(
        self, symbol: str, bar: pd.Series, timestamp: pd.Timestamp,
    ) -> None:
        """Force-close when maintenance margin ratio drops to / below 100%."""
        pos = self.positions.get(symbol)
        if pos is None or pos.leverage <= 1.0:
            return  # spot has no liquidation

        mark_price = float(bar.get("close", pos.entry_price))
        margin = pos.size * pos.entry_price / pos.leverage
        unrealized = pos.direction * pos.size * (mark_price - pos.entry_price)

        # Maintenance margin rate (tiered)
        notional = pos.size * mark_price
        maint_rate = self._maintenance_rate(notional)
        maint_margin = notional * maint_rate

        # Margin ratio = (margin + unrealized) / maint_margin
        equity_in_pos = margin + unrealized
        if equity_in_pos <= maint_margin:
            # Liquidation: close at mark price with taker fee
            liq_price = self.apply_slippage(mark_price, -pos.direction)
            self._close_position(symbol, liq_price, timestamp, "liquidation")

    @staticmethod
    def _maintenance_rate(notional_usd: float) -> float:
        """Look up tiered maintenance margin rate."""
        for tier_max, rate in _TIER_TABLE:
            if notional_usd <= tier_max:
                return rate
        return _TIER_TABLE[-1][1]
