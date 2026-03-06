"""Commodity price data source.

Provides access to fuel and carbon prices that drive European energy markets:
- TTF natural gas (Dutch hub)
- API2 coal
- EUA carbon allowances
- Brent crude oil

Note: Many commodity data sources require paid subscriptions.
This module provides a framework for ingesting commodity prices from
various sources (APIs, CSV uploads, manual entry).
"""

import os
from datetime import datetime

import pandas as pd

from app.data.sources.base import BaseDataSource

# Key commodity series for European energy price forecasting
COMMODITY_SERIES = {
    "ttf_gas_front_month": {
        "description": "TTF Natural Gas Front Month (EUR/MWh)",
        "unit": "EUR/MWh",
    },
    "ttf_gas_front_year": {
        "description": "TTF Natural Gas Front Year (EUR/MWh)",
        "unit": "EUR/MWh",
    },
    "api2_coal_front_month": {
        "description": "API2 Coal Front Month (USD/t)",
        "unit": "USD/t",
    },
    "eua_carbon_front_dec": {
        "description": "EUA Carbon Allowance Front December (EUR/tCO2)",
        "unit": "EUR/tCO2",
    },
    "brent_crude_front_month": {
        "description": "Brent Crude Oil Front Month (USD/bbl)",
        "unit": "USD/bbl",
    },
}


class CommodityDataSource(BaseDataSource):
    """Connector for commodity price data.

    Currently a placeholder that supports CSV-based data ingestion.
    Can be extended with specific API integrations (e.g., Quandl, ICE, EEX).
    """

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key or os.environ.get("COMMODITY_API_KEY"))

    def fetch(
        self,
        series_key: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Fetch commodity price data.

        series_key: one of the keys in COMMODITY_SERIES
        """
        if series_key not in COMMODITY_SERIES:
            raise ValueError(f"Unknown commodity series: {series_key}")

        # TODO: Implement actual data fetching
        # Options include:
        # - Quandl/Nasdaq Data Link API
        # - ICE API (subscription required)
        # - EEX API
        # - Yahoo Finance (limited commodity data)
        # - Manual CSV upload endpoint
        return pd.DataFrame(columns=["timestamp", "value"])

    def list_available_series(self) -> list[dict]:
        """List available commodity series."""
        return [
            {"key": key, **info}
            for key, info in COMMODITY_SERIES.items()
        ]
