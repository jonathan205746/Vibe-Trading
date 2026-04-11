"""DataLoader Protocol and shared exceptions for all data source loaders."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


class NoAvailableSourceError(Exception):
    """Raised when no data source is available for a given market."""


def validate_date_range(start_date: str, end_date: str) -> None:
    """Validate that start_date <= end_date.

    Args:
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).

    Raises:
        ValueError: If dates are invalid or start > end.
    """
    try:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
    except Exception as exc:
        raise ValueError(f"Invalid date format: start={start_date!r}, end={end_date!r}") from exc
    if start > end:
        raise ValueError(f"start_date ({start_date}) > end_date ({end_date})")


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
