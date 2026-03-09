"""Management CLI for data ingestion and forecasting.

Usage (from backend/):
    python -m app.manage ingest --days 365
    python -m app.manage ingest --start 2024-01-01 --end 2025-01-01
    python -m app.manage forecast
    python -m app.manage seed

Works locally and on Railway (`railway run python -m app.manage ingest`).
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models import SeriesDefinition, ForecastTarget
from app.data.pipeline import fetch_and_store
from app.forecasting.pipeline import run_forecast

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("manage")


def cmd_seed():
    """Seed the database with default records."""
    Base.metadata.create_all(bind=engine)
    from app.seed import seed
    seed()


def cmd_ingest(args):
    """Ingest data for all series in a market."""
    Base.metadata.create_all(bind=engine)

    end = datetime.strptime(args.end, "%Y-%m-%d") if args.end else datetime.utcnow()
    if args.start:
        start = datetime.strptime(args.start, "%Y-%m-%d")
    else:
        start = end - timedelta(days=args.days)

    db = SessionLocal()
    try:
        series_list = (
            db.query(SeriesDefinition)
            .filter(SeriesDefinition.market_id == args.market_id)
            .all()
        )
        if not series_list:
            # Try fetching all series if no market filter
            series_list = db.query(SeriesDefinition).all()

        if not series_list:
            logger.error("No series found. Run 'seed' first.")
            return

        for series in series_list:
            logger.info("=== Ingesting: %s (id=%d) ===", series.name, series.id)
            try:
                count = fetch_and_store(db, series, start, end)
                logger.info("Stored %d new points for %s", count, series.name)
            except Exception as e:
                logger.error("Failed to ingest %s: %s", series.name, e)
    finally:
        db.close()


def cmd_forecast(args):
    """Run a forecast for a target."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if args.target_id:
            targets = [db.query(ForecastTarget).filter(ForecastTarget.id == args.target_id).first()]
        else:
            targets = db.query(ForecastTarget).all()

        if not targets or targets[0] is None:
            logger.error("No forecast targets found. Run 'seed' first.")
            return

        for target in targets:
            logger.info("=== Running forecast: %s (id=%d) ===", target.name, target.id)
            forecast_start = datetime.strptime(args.forecast_start, "%Y-%m-%d") if args.forecast_start else datetime.utcnow()
            training_start = datetime.strptime(args.training_start, "%Y-%m-%d") if args.training_start else None

            run = run_forecast(db, target.id, forecast_start, training_start)
            logger.info("Forecast run %d: status=%s", run.id, run.status)
            if run.metrics_json:
                logger.info("Metrics: %s", run.metrics_json)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="AmonHen management CLI")
    sub = parser.add_subparsers(dest="command")

    # seed
    sub.add_parser("seed", help="Seed database with default records")

    # ingest
    ingest_p = sub.add_parser("ingest", help="Ingest data from external sources")
    ingest_p.add_argument("--market-id", type=int, default=1, help="Market ID (default: 1)")
    ingest_p.add_argument("--days", type=int, default=365, help="Days of history to fetch (default: 365)")
    ingest_p.add_argument("--start", type=str, default=None, help="Start date (YYYY-MM-DD)")
    ingest_p.add_argument("--end", type=str, default=None, help="End date (YYYY-MM-DD)")

    # forecast
    fc_p = sub.add_parser("forecast", help="Run forecast")
    fc_p.add_argument("--target-id", type=int, default=None, help="Forecast target ID (default: all)")
    fc_p.add_argument("--forecast-start", type=str, default=None, help="Forecast start (YYYY-MM-DD)")
    fc_p.add_argument("--training-start", type=str, default=None, help="Training start (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.command == "seed":
        cmd_seed()
    elif args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "forecast":
        cmd_forecast(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
