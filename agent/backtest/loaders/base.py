"""DataLoader Protocol and shared exceptions for all data source loaders."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


class NoAvailableSourceError(Exception):
    """Raised when no data source is available for a given market."""


@runtime_checkable
class DataLoaderProtocol(Protocol):
    """Interface that every data source loader must satisfy."""

    name: str
    markets: set[str]
    requires_auth: bool

    def is_available(self) -> bool:
        """Check whether this data source is usable (token present, network ok, etc.)."""
        ...

    def fetch(
        self,
        codes: list[str],
        start_date: str,
        end_date: str,
        *,
        interval: str = "1D",
        fields: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Fetch OHLCV data.

        Returns:
            Mapping ``{symbol: DataFrame(trade_date, open, high, low, close, volume)}``.
        """
        ...
