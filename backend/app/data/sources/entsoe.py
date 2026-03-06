"""ENTSO-E Transparency Platform data source.

Provides access to:
- Day-ahead prices (all EU bidding zones)
- Actual load and load forecasts
- Wind and solar generation forecasts and actuals
- Generation by fuel type
- Cross-border physical flows

API documentation: https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
"""

import os
from datetime import datetime

import pandas as pd

from app.data.sources.base import BaseDataSource

# ENTSO-E area codes for major European bidding zones
BIDDING_ZONES = {
    "DE_LU": "10Y1001A1001A82H",  # Germany-Luxembourg
    "FR": "10YFR-RTE------C",     # France
    "NL": "10YNL----------L",     # Netherlands
    "BE": "10YBE----------2",     # Belgium
    "AT": "10YAT-APG------L",     # Austria
    "ES": "10YES-REE------0",     # Spain
    "PT": "10YPT-REN------W",     # Portugal
    "IT_NORD": "10Y1001A1001A73I", # Italy North
    "CH": "10YCH-SWISSGRIDZ",     # Switzerland
    "PL": "10YPL-AREA-----S",     # Poland
    "CZ": "10YCZ-CEPS-----N",     # Czech Republic
    "DK1": "10YDK-1--------W",    # Denmark West
    "DK2": "10YDK-2--------M",    # Denmark East
    "SE1": "10Y1001A1001A44P",    # Sweden 1
    "SE2": "10Y1001A1001A45N",    # Sweden 2
    "SE3": "10Y1001A1001A46L",    # Sweden 3
    "SE4": "10Y1001A1001A47J",    # Sweden 4
    "NO1": "10YNO-1--------2",    # Norway 1
    "NO2": "10YNO-2--------T",    # Norway 2
    "FI": "10YFI-1--------U",     # Finland
}

# ENTSO-E document type codes
DOCUMENT_TYPES = {
    "day_ahead_prices": "A44",
    "actual_load": "A65",
    "load_forecast": "A65",
    "wind_solar_forecast": "A69",
    "actual_generation_per_type": "A75",
    "installed_generation_capacity": "A68",
}

BASE_URL = "https://web-api.tp.entsoe.eu/api"


class EntsoeDataSource(BaseDataSource):
    """Connector for the ENTSO-E Transparency Platform REST API."""

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key or os.environ.get("ENTSOE_API_KEY"))
        self.base_url = BASE_URL

    def fetch(
        self,
        series_key: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Fetch data from ENTSO-E.

        series_key format: "{document_type}:{bidding_zone}"
        e.g. "day_ahead_prices:DE_LU"
        """
        doc_type_name, zone = series_key.split(":")
        doc_type = DOCUMENT_TYPES[doc_type_name]
        area_code = BIDDING_ZONES[zone]

        params = {
            "securityToken": self.api_key,
            "documentType": doc_type,
            "in_Domain": area_code,
            "out_Domain": area_code,
            "periodStart": start.strftime("%Y%m%d%H%M"),
            "periodEnd": end.strftime("%Y%m%d%H%M"),
        }

        # TODO: Implement actual HTTP request and XML parsing
        # The ENTSO-E API returns XML that needs to be parsed into a DataFrame
        # For now, return empty DataFrame with correct schema
        return pd.DataFrame(columns=["timestamp", "value"])

    def list_available_series(self) -> list[dict]:
        """List all available ENTSO-E series combinations."""
        series = []
        for doc_name, doc_code in DOCUMENT_TYPES.items():
            for zone_name in BIDDING_ZONES:
                series.append({
                    "key": f"{doc_name}:{zone_name}",
                    "description": f"{doc_name.replace('_', ' ').title()} for {zone_name}",
                    "document_type": doc_code,
                    "bidding_zone": zone_name,
                })
        return series
