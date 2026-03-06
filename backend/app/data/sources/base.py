"""Base class for all data sources."""

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class BaseDataSource(ABC):
    """Abstract base class for data source connectors.

    Each data source implementation handles fetching data from a specific
    external API and returning it as a standardized pandas DataFrame with
    columns: [timestamp, value].
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    @abstractmethod
    def fetch(
        self,
        series_key: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Fetch data for a given series key and time range.

        Args:
            series_key: Identifier for the specific data series (source-specific).
            start: Start of the time range.
            end: End of the time range.

        Returns:
            DataFrame with columns ['timestamp', 'value'].
        """

    @abstractmethod
    def list_available_series(self) -> list[dict]:
        """List available series from this source.

        Returns:
            List of dicts with at least 'key' and 'description' fields.
        """
