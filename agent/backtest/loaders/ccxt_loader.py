"""CCXT loader: unified crypto exchange data (100+ exchanges).

Uses the CCXT library to fetch OHLCV candles from any supported exchange.
Defaults to Binance; configurable via CCXT_EXCHANGE env var.
No API key required for public market data.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

import pandas as pd

from backtest.loaders.registry import register

logger = logging.getLogger(__name__)

_INTERVAL_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1H": "1h", "4H": "4h", "1D": "1d",
}


@register
class DataLoader:
    """CCXT-backed crypto OHLCV loader (100+ exchanges)."""

    name = "ccxt"
    markets = {"crypto"}
    requires_auth = False

    def is_available(self) -> bool:
        """Available if ccxt is installed."""
        try:
            import ccxt  # noqa: F401
            return True
        except ImportError:
            return False

    def __init__(self) -> None:
        pass

    def _get_exchange(self):
        """Create exchange instance."""
        import ccxt
        exchange_id = os.getenv("CCXT_EXCHANGE", "binance").lower()
        exchange_cls = getattr(ccxt, exchange_id, None)
        if exchange_cls is None:
            logger.warning("Unknown CCXT exchange %s, falling back to binance", exchange_id)
            exchange_cls = ccxt.binance
        return exchange_cls({"enableRateLimit": True})

    def fetch(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        *,
        interval: str = "1D",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch crypto OHLCV via CCXT.

        Args:
            codes: Symbols like ``["BTC-USDT", "ETH-USDT"]``.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            interval: Bar size.
            fields: Ignored.

        Returns:
            Mapping symbol -> OHLCV DataFrame.
        """
        exchange = self._get_exchange()
        timeframe = _INTERVAL_MAP.get(interval, "1d")
        since_ms = int(pd.Timestamp(start_date).timestamp() * 1000)
        end_ms = int((pd.Timestamp(end_date) + pd.Timedelta(days=1)).timestamp() * 1000)

        result: Dict[str, pd.DataFrame] = {}
        for code in codes:
            try:
                ccxt_symbol = code.replace("-", "/").upper()
                df = self._fetch_one(exchange, ccxt_symbol, timeframe, since_ms, end_ms)
                if df is not None and not df.empty:
                    result[code] = df
            except Exception as exc:
                logger.warning("CCXT failed for %s: %s", code, exc)
        return result

    @staticmethod
    def _fetch_one(
        exchange, symbol: str, timeframe: str, since_ms: int, end_ms: int,
    ) -> Optional[pd.DataFrame]:
        """Paginated OHLCV fetch for one symbol."""
        all_rows: list = []
        cursor = since_ms
        limit = 1000

        for _ in range(200):
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=cursor, limit=limit)
            if not ohlcv:
                break
            all_rows.extend(ohlcv)
            last_ts = ohlcv[-1][0]
            if last_ts >= end_ms or len(ohlcv) < limit:
                break
            cursor = last_ts + 1

        if not all_rows:
            return None

        df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["trade_date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("trade_date").sort_index()

        start_dt = pd.Timestamp(since_ms, unit="ms")
        end_dt = pd.Timestamp(end_ms, unit="ms")
        df = df[(df.index >= start_dt) & (df.index < end_dt)]

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df[["open", "high", "low", "close", "volume"]].dropna(
            subset=["open", "high", "low", "close"]
        )
        return df if not df.empty else None
