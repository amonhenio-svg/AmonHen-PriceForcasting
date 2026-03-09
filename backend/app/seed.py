"""Seed the database with initial market, data source, and series definitions.

Run this script to set up the German Day-Ahead market with all the ENTSO-E
series needed for forecasting. Safe to run multiple times -- skips records
that already exist.

Usage:
    python -m app.seed          (from backend/)
    python app/seed.py          (from backend/)
"""

import json
import logging
import sys
import os

# Allow running as `python app/seed.py` from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Market, DataSource, SeriesDefinition, ForecastTarget

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_or_create(db, model, filter_kwargs, create_kwargs=None):
    """Get existing record or create a new one. Returns (instance, created)."""
    instance = db.query(model).filter_by(**filter_kwargs).first()
    if instance:
        return instance, False
    instance = model(**filter_kwargs, **(create_kwargs or {}))
    db.add(instance)
    db.flush()
    return instance, True


def seed():
    db = SessionLocal()
    try:
        # --- Data Sources ---
        entsoe, created = get_or_create(db, DataSource,
            {"name": "ENTSO-E Transparency Platform"},
            {"source_type": "entsoe",
             "base_url": "https://web-api.tp.entsoe.eu/api",
             "api_key_env_var": "ENTSOE_API_KEY"})
        if created:
            logger.info("Created data source: ENTSO-E")

        open_meteo, created = get_or_create(db, DataSource,
            {"name": "Open-Meteo Weather"},
            {"source_type": "open_meteo",
             "base_url": "https://api.open-meteo.com/v1"})
        if created:
            logger.info("Created data source: Open-Meteo")

        # --- Markets ---
        de_market, created = get_or_create(db, Market,
            {"name": "Germany Day-Ahead"},
            {"country": "DE",
             "commodity": "electricity",
             "market_type": "day_ahead",
             "timezone": "Europe/Berlin",
             "granularity_minutes": 60,
             "currency": "EUR",
             "unit": "MWh"})
        if created:
            logger.info("Created market: Germany Day-Ahead")

        # --- Series Definitions ---
        series_defs = [
            {
                "name": "DE Day-Ahead Price",
                "category": "price",
                "data_source_id": entsoe.id,
                "market_id": de_market.id,
                "unit": "EUR/MWh",
                "granularity_minutes": 60,
                "source_series_key": "day_ahead_prices:DE_LU",
            },
            {
                "name": "DE Actual Load",
                "category": "load",
                "data_source_id": entsoe.id,
                "market_id": de_market.id,
                "unit": "MW",
                "granularity_minutes": 60,
                "source_series_key": "actual_load:DE_LU",
            },
            {
                "name": "DE Load Forecast",
                "category": "load",
                "data_source_id": entsoe.id,
                "market_id": de_market.id,
                "unit": "MW",
                "granularity_minutes": 60,
                "source_series_key": "load_forecast:DE_LU",
            },
            {
                "name": "DE Wind+Solar Forecast",
                "category": "generation",
                "data_source_id": entsoe.id,
                "market_id": de_market.id,
                "unit": "MW",
                "granularity_minutes": 60,
                "source_series_key": "wind_solar_forecast:DE_LU",
            },
        ]

        series_ids = {}
        for sd in series_defs:
            instance, created = get_or_create(db, SeriesDefinition,
                {"name": sd["name"]}, {k: v for k, v in sd.items() if k != "name"})
            series_ids[sd["name"]] = instance.id
            if created:
                logger.info("Created series: %s (id=%d)", sd["name"], instance.id)

        # --- Forecast Target ---
        price_series_id = series_ids["DE Day-Ahead Price"]
        load_series_id = series_ids["DE Actual Load"]
        wind_solar_id = series_ids["DE Wind+Solar Forecast"]

        model_config = json.dumps({
            "target_series_id": price_series_id,
            "feature_series_ids": [load_series_id, wind_solar_id],
            "models": ["xgboost"],
        })

        _, created = get_or_create(db, ForecastTarget,
            {"name": "DE Day-Ahead 24h Forecast"},
            {"market_id": de_market.id,
             "horizon_hours": 24,
             "granularity_minutes": 60,
             "model_config_json": model_config})
        if created:
            logger.info("Created forecast target: DE Day-Ahead 24h Forecast")

        db.commit()
        logger.info("Seed complete.")

        # Print summary
        logger.info("--- Summary ---")
        logger.info("Market: Germany Day-Ahead (id=%d)", de_market.id)
        logger.info("Data source: ENTSO-E (id=%d)", entsoe.id)
        for name, sid in series_ids.items():
            logger.info("Series: %s (id=%d)", name, sid)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
