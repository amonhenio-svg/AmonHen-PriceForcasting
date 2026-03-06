"""ENTSO-E Transparency Platform data source.

Provides access to:
- Day-ahead prices (all EU bidding zones)
- Actual load and load forecasts
- Wind and solar generation forecasts and actuals
- Generation by fuel type
- Cross-border physical flows

API documentation: https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
"""

import logging
import os
from datetime import datetime
from xml.etree import ElementTree

import pandas as pd
import requests

from app.data.sources.base import BaseDataSource

logger = logging.getLogger(__name__)

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

# Process type codes (used to distinguish load actual vs forecast)
PROCESS_TYPES = {
    "actual_load": "A16",
    "load_forecast": "A01",
    "wind_solar_forecast": "A01",
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
        if not self.api_key:
            raise ValueError(
                "ENTSO-E API key required. Set ENTSOE_API_KEY environment variable "
                "or register at https://transparency.entsoe.eu/"
            )

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

        # Add process type for load/generation queries
        if doc_type_name in PROCESS_TYPES:
            params["processType"] = PROCESS_TYPES[doc_type_name]

        logger.info("ENTSO-E request: %s %s -> %s", doc_type_name, zone, area_code)
        response = requests.get(self.base_url, params=params, timeout=60)
        response.raise_for_status()

        return self._parse_xml(response.text)

    def _parse_xml(self, xml_text: str) -> pd.DataFrame:
        """Parse ENTSO-E XML response into a DataFrame.

        The XML structure varies by document type but generally follows:
        <Publication_MarketDocument> or <GL_MarketDocument>
          <TimeSeries>
            <Period>
              <timeInterval>
                <start>2024-01-01T00:00Z</start>
                <end>2024-01-02T00:00Z</end>
              </timeInterval>
              <resolution>PT60M</resolution>
              <Point>
                <position>1</position>
                <price.amount>45.32</price.amount>  (for prices)
                <quantity>12345.6</quantity>          (for load/generation)
              </Point>
              ...
            </Period>
          </TimeSeries>
        """
        root = ElementTree.fromstring(xml_text)

        # Detect namespace from root tag: {urn:...}DocumentName -> urn:...
        ns_uri = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
        ns = {"ns": ns_uri} if ns_uri else {}

        rows = []

        ts_tag = "ns:TimeSeries" if ns else "TimeSeries"
        for ts in root.findall(f".//{ts_tag}", ns):
            for period in ts.findall("ns:Period" if ns else "Period", ns):
                # Find period start time
                start_el = (
                    period.find(".//ns:start", ns)
                    if ns else period.find(".//start")
                )
                resolution_el = (
                    period.find("ns:resolution", ns)
                    if ns else period.find("resolution")
                )

                if start_el is None or start_el.text is None:
                    continue

                period_start = pd.Timestamp(start_el.text)
                resolution_text = (
                    resolution_el.text
                    if resolution_el is not None and resolution_el.text
                    else "PT60M"
                )
                resolution = self._parse_resolution(resolution_text)

                point_tag = "ns:Point" if ns else "Point"
                for point in period.findall(point_tag, ns):
                    pos_el = (
                        point.find("ns:position", ns)
                        if ns else point.find("position")
                    )
                    if pos_el is None or pos_el.text is None:
                        continue
                    position = int(pos_el.text)

                    # Try price.amount first (price docs), then quantity (load/gen docs)
                    value = None
                    for value_tag in ["price.amount", "quantity"]:
                        tag = f"ns:{value_tag}" if ns else value_tag
                        val_el = point.find(tag, ns)
                        if val_el is not None and val_el.text is not None:
                            value = float(val_el.text)
                            break

                    if value is not None:
                        timestamp = period_start + resolution * (position - 1)
                        rows.append({"timestamp": timestamp, "value": value})

        if not rows:
            logger.warning("No data points parsed from ENTSO-E XML response")
            return pd.DataFrame(columns=["timestamp", "value"])

        df = pd.DataFrame(rows)
        df = df.sort_values("timestamp").reset_index(drop=True)
        logger.info("Parsed %d data points from ENTSO-E", len(df))
        return df

    @staticmethod
    def _parse_resolution(resolution: str) -> pd.Timedelta:
        """Parse ISO 8601 duration string to pandas Timedelta."""
        resolution = resolution.upper()
        if resolution in ("PT60M", "PT1H"):
            return pd.Timedelta(hours=1)
        if resolution == "PT30M":
            return pd.Timedelta(minutes=30)
        if resolution == "PT15M":
            return pd.Timedelta(minutes=15)
        if resolution == "P1D":
            return pd.Timedelta(days=1)
        return pd.Timedelta(resolution)

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
