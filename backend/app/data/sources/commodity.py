"""Commodity price data source using Yahoo Finance.

Provides access to fuel and carbon prices that drive European energy markets:
- TTF natural gas (Dutch hub)
- API2 coal
- EUA carbon allowances
- Brent crude oil
- German power baseload futures (EEX)

Yahoo Finance provides free delayed data for most commodity futures.
For real-time or more comprehensive forward curves, integrate a premium
data source (EEX API, ICE API, Nasdaq Data Link) by subclassing.
"""

import logging
import os
from datetime import datetime, timedelta

import pandas as pd

from app.data.sources.base import BaseDataSource

logger = logging.getLogger(__name__)

# Yahoo Finance tickers and metadata for European energy commodities
COMMODITY_SERIES = {
    # --- Fuel inputs ---
    "ttf_gas_front_month": {
        "description": "TTF Natural Gas Front Month (EUR/MWh)",
        "unit": "EUR/MWh",
        "yahoo_ticker": "TTF=F",
    },
    "brent_crude_front_month": {
        "description": "Brent Crude Oil Front Month (USD/bbl)",
        "unit": "USD/bbl",
        "yahoo_ticker": "BZ=F",
    },
    "natural_gas_henry_hub": {
        "description": "Henry Hub Natural Gas Front Month (USD/MMBtu)",
        "unit": "USD/MMBtu",
        "yahoo_ticker": "NG=F",
    },
    "api2_coal_front_month": {
        "description": "API2 Coal Front Month (USD/t) — proxied via Newcastle coal",
        "unit": "USD/t",
        "yahoo_ticker": "MTF=F",
    },
    # --- Carbon ---
    "eua_carbon_front_dec": {
        "description": "EUA Carbon Allowance — proxied via KraneShares Carbon ETF",
        "unit": "EUR/tCO2",
        "yahoo_ticker": "KRBN",
    },
    # --- Power futures (EEX German baseload) ---
    # Note: EEX power futures aren't on Yahoo Finance. These are fetched
    # separately via the EEX data source or manual CSV. The keys are kept
    # here for the registry / seeding, but fetch() handles them via
    # _fetch_eex_power() when available.
    "de_power_baseload_month_ahead": {
        "description": "German Baseload Month-Ahead (EUR/MWh)",
        "unit": "EUR/MWh",
        "yahoo_ticker": None,  # not on Yahoo; needs EEX or manual
    },
    "de_power_baseload_quarter_ahead": {
        "description": "German Baseload Quarter-Ahead (EUR/MWh)",
        "unit": "EUR/MWh",
        "yahoo_ticker": None,
    },
    "de_power_baseload_year_ahead": {
        "description": "German Baseload Year-Ahead (Cal+1) (EUR/MWh)",
        "unit": "EUR/MWh",
        "yahoo_ticker": None,
    },
}


class CommodityDataSource(BaseDataSource):
    """Connector for commodity and power futures price data.

    Uses Yahoo Finance (via yfinance) for fuel and carbon commodities.
    Power baseload futures need a premium source — the framework is ready
    but fetch returns empty data for those until configured.
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

        Returns a DataFrame with columns ['timestamp', 'value'].
        Daily commodity prices are forward-filled to hourly to align
        with the hourly electricity price series.
        """
        if series_key not in COMMODITY_SERIES:
            raise ValueError(f"Unknown commodity series: {series_key}")

        spec = COMMODITY_SERIES[series_key]
        ticker = spec.get("yahoo_ticker")

        if ticker is None:
            # Power futures — not available via Yahoo Finance
            logger.warning(
                "Series '%s' requires a premium data source (EEX/ICE). "
                "Returning empty DataFrame. Configure EEX_API_KEY or upload CSV.",
                series_key,
            )
            return pd.DataFrame(columns=["timestamp", "value"])

        return self._fetch_yahoo(ticker, start, end)

    def _fetch_yahoo(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Fetch daily close prices from Yahoo Finance and resample to hourly."""
        try:
            import yfinance as yf
        except ImportError:
            logger.error(
                "yfinance not installed. Run: pip install yfinance"
            )
            return pd.DataFrame(columns=["timestamp", "value"])

        # Fetch daily data with a small buffer for forward-fill
        fetch_start = start - timedelta(days=7)
        logger.info("Fetching Yahoo Finance data for %s (%s to %s)", ticker, fetch_start.date(), end.date())

        try:
            data = yf.download(
                ticker,
                start=fetch_start.strftime("%Y-%m-%d"),
                end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
                auto_adjust=True,
                progress=False,
            )
        except Exception as e:
            logger.error("Yahoo Finance fetch failed for %s: %s", ticker, e)
            return pd.DataFrame(columns=["timestamp", "value"])

        if data.empty:
            logger.warning("No data returned from Yahoo Finance for %s", ticker)
            return pd.DataFrame(columns=["timestamp", "value"])

        # Use 'Close' price; flatten MultiIndex if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        close = data[["Close"]].copy()
        close = close.rename(columns={"Close": "value"})
        close.index.name = "timestamp"
        close = close.reset_index()

        # Ensure timezone-naive UTC timestamps
        if close["timestamp"].dt.tz is not None:
            close["timestamp"] = close["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)

        # Resample daily → hourly via forward-fill so it aligns with
        # hourly electricity data
        close = close.set_index("timestamp")
        hourly = close.resample("h").ffill()
        hourly = hourly.reset_index()

        # Trim to requested range
        mask = (hourly["timestamp"] >= pd.Timestamp(start)) & (hourly["timestamp"] <= pd.Timestamp(end))
        hourly = hourly.loc[mask].copy()

        logger.info("Fetched %d hourly points for %s", len(hourly), ticker)
        return hourly[["timestamp", "value"]]

    def list_available_series(self) -> list[dict]:
        """List available commodity series."""
        return [
            {"key": key, **{k: v for k, v in info.items() if k != "yahoo_ticker"}}
            for key, info in COMMODITY_SERIES.items()
        ]
