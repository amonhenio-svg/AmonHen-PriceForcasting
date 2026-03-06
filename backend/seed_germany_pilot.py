"""Seed script: Set up Germany Day-Ahead as the first pilot market.

Creates:
1. DE-LU Day-Ahead market
2. Data sources (ENTSO-E, Open-Meteo)
3. Series definitions (prices, load, weather, generation)
4. Forecast target (24h ahead day-ahead price)

Run with: python -m seed_germany_pilot
"""

import json
import sys
import os

# Ensure the backend app is importable
sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base, engine, SessionLocal
from app.models import (
    Market,
    DataSource,
    SeriesDefinition,
    ForecastTarget,
)


def seed():
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        existing = db.query(Market).filter(Market.name == "DE-LU Day-Ahead").first()
        if existing:
            print("Already seeded. Skipping.")
            return

        # 1. Create the Germany-Luxembourg Day-Ahead market
        market = Market(
            name="DE-LU Day-Ahead",
            country="DE",
            commodity="electricity",
            market_type="day_ahead",
            timezone="Europe/Berlin",
            granularity_minutes=60,
            currency="EUR",
            unit="MWh",
        )
        db.add(market)
        db.flush()
        print(f"Created market: {market.name} (id={market.id})")

        # 2. Create data sources
        entsoe = DataSource(
            name="ENTSO-E Transparency",
            source_type="entsoe",
            base_url="https://web-api.tp.entsoe.eu/api",
            api_key_env_var="ENTSOE_API_KEY",
        )
        open_meteo = DataSource(
            name="Open-Meteo Weather",
            source_type="open_meteo",
            base_url="https://api.open-meteo.com/v1",
        )
        db.add_all([entsoe, open_meteo])
        db.flush()
        print(f"Created data sources: ENTSO-E (id={entsoe.id}), Open-Meteo (id={open_meteo.id})")

        # 3. Create series definitions
        series_defs = [
            # Price series
            SeriesDefinition(
                name="DE-LU Day-Ahead Price",
                category="price",
                data_source_id=entsoe.id,
                market_id=market.id,
                unit="EUR/MWh",
                granularity_minutes=60,
                source_series_key="day_ahead_prices:DE_LU",
            ),
            # Load series
            SeriesDefinition(
                name="DE-LU Actual Load",
                category="load",
                data_source_id=entsoe.id,
                market_id=market.id,
                unit="MW",
                granularity_minutes=60,
                source_series_key="actual_load:DE_LU",
            ),
            SeriesDefinition(
                name="DE-LU Load Forecast",
                category="load",
                data_source_id=entsoe.id,
                market_id=market.id,
                unit="MW",
                granularity_minutes=60,
                source_series_key="load_forecast:DE_LU",
            ),
            # Generation series
            SeriesDefinition(
                name="DE-LU Wind+Solar Forecast",
                category="generation",
                data_source_id=entsoe.id,
                market_id=market.id,
                unit="MW",
                granularity_minutes=60,
                source_series_key="wind_solar_forecast:DE_LU",
            ),
            # Weather series
            SeriesDefinition(
                name="DE Temperature",
                category="weather",
                data_source_id=open_meteo.id,
                market_id=market.id,
                unit="C",
                granularity_minutes=60,
                source_series_key="temperature_2m:DE_LU",
            ),
            SeriesDefinition(
                name="DE Wind Speed 100m",
                category="weather",
                data_source_id=open_meteo.id,
                market_id=market.id,
                unit="m/s",
                granularity_minutes=60,
                source_series_key="windspeed_100m:DE_LU",
            ),
            SeriesDefinition(
                name="DE Solar Radiation",
                category="weather",
                data_source_id=open_meteo.id,
                market_id=market.id,
                unit="W/m2",
                granularity_minutes=60,
                source_series_key="shortwave_radiation:DE_LU",
            ),
        ]
        db.add_all(series_defs)
        db.flush()
        for s in series_defs:
            print(f"  Series: {s.name} (id={s.id}, key={s.source_series_key})")

        # 4. Create forecast target
        # Reference the series IDs for the feature config
        price_series = next(s for s in series_defs if s.category == "price")
        feature_ids = [s.id for s in series_defs if s.category != "price"]

        forecast_config = {
            "target_series_id": price_series.id,
            "feature_series_ids": feature_ids,
            "models": ["xgboost"],
            "xgboost_params": {
                "n_estimators": 500,
                "max_depth": 6,
                "learning_rate": 0.05,
            },
        }

        target = ForecastTarget(
            market_id=market.id,
            name="DE-LU 24h Day-Ahead Price",
            horizon_hours=24,
            granularity_minutes=60,
            model_config_json=json.dumps(forecast_config),
        )
        db.add(target)
        db.flush()
        print(f"Created forecast target: {target.name} (id={target.id})")

        db.commit()
        print("\nSeed complete! Germany Day-Ahead pilot is ready.")
        print(f"\nMarket ID: {market.id}")
        print(f"Price series ID: {price_series.id}")
        print(f"Forecast target ID: {target.id}")
        print(f"\nNext steps:")
        print(f"  1. Set ENTSOE_API_KEY env var (register at https://transparency.entsoe.eu/)")
        print(f"  2. Start the API: cd backend && uvicorn app.main:app --reload")
        print(f"  3. Start the frontend: cd frontend && npm start")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
