"""Open-Meteo weather data source.

Provides access to:
- Historical weather data (temperature, wind speed, solar radiation, etc.)
- Weather forecasts (up to 16 days ahead)

API documentation: https://open-meteo.com/en/docs
Free, no API key required.
"""

from datetime import datetime

import pandas as pd

from app.data.sources.base import BaseDataSource

# Representative locations for weather data per bidding zone
# Using approximate centroids of major demand areas
ZONE_LOCATIONS = {
    "DE_LU": {"lat": 51.0, "lon": 10.0, "name": "Germany (central)"},
    "FR": {"lat": 46.6, "lon": 2.5, "name": "France (central)"},
    "NL": {"lat": 52.1, "lon": 5.3, "name": "Netherlands"},
    "BE": {"lat": 50.8, "lon": 4.4, "name": "Belgium"},
    "AT": {"lat": 47.5, "lon": 14.0, "name": "Austria"},
    "ES": {"lat": 40.4, "lon": -3.7, "name": "Spain (central)"},
    "PT": {"lat": 39.4, "lon": -8.2, "name": "Portugal"},
    "IT_NORD": {"lat": 45.5, "lon": 10.0, "name": "Italy North"},
    "CH": {"lat": 46.8, "lon": 8.2, "name": "Switzerland"},
    "PL": {"lat": 52.0, "lon": 20.0, "name": "Poland"},
    "CZ": {"lat": 49.8, "lon": 15.5, "name": "Czech Republic"},
    "DK1": {"lat": 56.0, "lon": 9.0, "name": "Denmark West"},
    "DK2": {"lat": 55.7, "lon": 12.6, "name": "Denmark East"},
    "NO1": {"lat": 60.0, "lon": 11.0, "name": "Norway South-East"},
    "SE3": {"lat": 59.3, "lon": 18.1, "name": "Sweden Stockholm"},
    "FI": {"lat": 61.0, "lon": 24.0, "name": "Finland"},
}

# Weather variables relevant for energy price forecasting
WEATHER_VARIABLES = [
    "temperature_2m",
    "windspeed_10m",
    "windspeed_100m",        # better proxy for wind turbine height
    "winddirection_10m",
    "shortwave_radiation",   # proxy for solar generation
    "direct_radiation",
    "diffuse_radiation",
    "cloudcover",
    "precipitation",
]

BASE_URL = "https://api.open-meteo.com/v1"


class OpenMeteoDataSource(BaseDataSource):
    """Connector for the Open-Meteo weather API (free, no key required)."""

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key=None)  # Open-Meteo is free
        self.base_url = BASE_URL

    def fetch(
        self,
        series_key: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Fetch weather data from Open-Meteo.

        series_key format: "{variable}:{zone}"
        e.g. "temperature_2m:DE_LU"
        """
        variable, zone = series_key.split(":")
        location = ZONE_LOCATIONS[zone]

        params = {
            "latitude": location["lat"],
            "longitude": location["lon"],
            "hourly": variable,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "timezone": "UTC",
        }

        # TODO: Implement actual HTTP request
        # Open-Meteo returns JSON that maps directly to a DataFrame
        # For now, return empty DataFrame with correct schema
        return pd.DataFrame(columns=["timestamp", "value"])

    def list_available_series(self) -> list[dict]:
        """List all available weather series combinations."""
        series = []
        for var in WEATHER_VARIABLES:
            for zone_name, loc in ZONE_LOCATIONS.items():
                series.append({
                    "key": f"{var}:{zone_name}",
                    "description": f"{var} at {loc['name']}",
                    "variable": var,
                    "zone": zone_name,
                    "lat": loc["lat"],
                    "lon": loc["lon"],
                })
        return series
