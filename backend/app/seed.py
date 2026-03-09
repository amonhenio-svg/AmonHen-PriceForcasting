"""Seed the database with initial market, data source, and series definitions.

Run this script to set up the German Day-Ahead market with all the ENTSO-E
series and commodity/forward curve inputs needed for forecasting.
Safe to run multiple times -- skips records that already exist.

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

        commodity_src, created = get_or_create(db, DataSource,
            {"name": "Commodity Futures (Yahoo Finance)"},
            {"source_type": "commodity",
             "base_url": "https://query1.finance.yahoo.com"})
        if created:
            logger.info("Created data source: Commodity Futures")

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

        # --- ENTSO-E Series Definitions ---
        entsoe_series = [
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

        # --- Commodity / Forward Curve Series ---
        commodity_series = [
            {
                "name": "TTF Gas Front Month",
                "category": "commodity",
                "data_source_id": commodity_src.id,
                "market_id": None,  # cross-market
                "unit": "EUR/MWh",
                "granularity_minutes": 60,
                "source_series_key": "ttf_gas_front_month",
            },
            {
                "name": "Brent Crude Front Month",
                "category": "commodity",
                "data_source_id": commodity_src.id,
                "market_id": None,
                "unit": "USD/bbl",
                "granularity_minutes": 60,
                "source_series_key": "brent_crude_front_month",
            },
            {
                "name": "EUA Carbon Front Dec",
                "category": "commodity",
                "data_source_id": commodity_src.id,
                "market_id": None,
                "unit": "EUR/tCO2",
                "granularity_minutes": 60,
                "source_series_key": "eua_carbon_front_dec",
            },
            {
                "name": "Natural Gas Henry Hub",
                "category": "commodity",
                "data_source_id": commodity_src.id,
                "market_id": None,
                "unit": "USD/MMBtu",
                "granularity_minutes": 60,
                "source_series_key": "natural_gas_henry_hub",
            },
        ]

        series_ids = {}
        for sd in entsoe_series + commodity_series:
            instance, created = get_or_create(db, SeriesDefinition,
                {"name": sd["name"]}, {k: v for k, v in sd.items() if k != "name"})
            series_ids[sd["name"]] = instance.id
            if created:
                logger.info("Created series: %s (id=%d)", sd["name"], instance.id)

        # --- Forecast Target ---
        price_series_id = series_ids["DE Day-Ahead Price"]
        load_series_id = series_ids["DE Actual Load"]
        wind_solar_id = series_ids["DE Wind+Solar Forecast"]

        # Forward curve series IDs — commodity prices that anchor the prediction
        ttf_gas_id = series_ids["TTF Gas Front Month"]
        brent_id = series_ids["Brent Crude Front Month"]
        eua_carbon_id = series_ids["EUA Carbon Front Dec"]

        model_config = json.dumps({
            "target_series_id": price_series_id,
            "feature_series_ids": [load_series_id, wind_solar_id],
            "forward_series_ids": [ttf_gas_id, brent_id, eua_carbon_id],
            "models": ["xgboost"],
        })

        target, created = get_or_create(db, ForecastTarget,
            {"name": "DE Day-Ahead 24h Forecast"},
            {"market_id": de_market.id,
             "horizon_hours": 24,
             "granularity_minutes": 60,
             "model_config_json": model_config})

        # Update config if target already exists (to pick up new forward_series_ids)
        if not created:
            existing_config = json.loads(target.model_config_json) if target.model_config_json else {}
            if "forward_series_ids" not in existing_config:
                existing_config["forward_series_ids"] = [ttf_gas_id, brent_id, eua_carbon_id]
                target.model_config_json = json.dumps(existing_config)
                logger.info("Updated forecast target with forward_series_ids")
        else:
            logger.info("Created forecast target: DE Day-Ahead 24h Forecast")

        db.commit()
        logger.info("Seed complete.")

        # Print summary
        logger.info("--- Summary ---")
        logger.info("Market: Germany Day-Ahead (id=%d)", de_market.id)
        logger.info("Data sources: ENTSO-E (id=%d), Commodity (id=%d)", entsoe.id, commodity_src.id)
        for name, sid in series_ids.items():
            logger.info("Series: %s (id=%d)", name, sid)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
