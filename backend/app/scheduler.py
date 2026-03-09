"""Background scheduler for daily data ingestion and forecasting.

Runs inside the FastAPI process using asyncio — no extra dependencies needed.
On startup, backfills historical data if the database is empty.
Then runs daily ingestion + forecast at a configurable hour (default: 06:00 UTC).
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta

from app.database import SessionLocal, Base, engine
from app.models import SeriesDefinition, ForecastTarget, TimeSeriesData
from app.data.pipeline import fetch_and_store
from app.forecasting.pipeline import run_forecast

logger = logging.getLogger("scheduler")

DAILY_HOUR_UTC = int(os.environ.get("INGEST_HOUR_UTC", "6"))
BACKFILL_DAYS = int(os.environ.get("BACKFILL_DAYS", "365"))


def _backfill_if_empty():
    """If no time series data exists, backfill BACKFILL_DAYS of history."""
    db = SessionLocal()
    try:
        count = db.query(TimeSeriesData).limit(1).count()
        if count > 0:
            logger.info("Database already has data, skipping backfill.")
            return False

        logger.info("Empty database detected — backfilling %d days of data...", BACKFILL_DAYS)
        end = datetime.utcnow()
        start = end - timedelta(days=BACKFILL_DAYS)

        series_list = db.query(SeriesDefinition).all()
        if not series_list:
            logger.warning("No series definitions found. Run seed first.")
            return False

        for series in series_list:
            try:
                n = fetch_and_store(db, series, start, end)
                logger.info("Backfill: %d points for %s", n, series.name)
            except Exception as e:
                logger.error("Backfill failed for %s: %s", series.name, e)

        return True
    finally:
        db.close()


def _daily_ingest():
    """Fetch yesterday's + today's data for all series."""
    db = SessionLocal()
    try:
        end = datetime.utcnow() + timedelta(days=1)  # include today fully
        start = end - timedelta(days=3)  # 3-day overlap for safety

        series_list = db.query(SeriesDefinition).all()
        total = 0
        for series in series_list:
            try:
                n = fetch_and_store(db, series, start, end)
                total += n
                logger.info("Daily ingest: %d new points for %s", n, series.name)
            except Exception as e:
                logger.error("Daily ingest failed for %s: %s", series.name, e)

        logger.info("Daily ingest complete: %d total new points", total)
        return total
    finally:
        db.close()


def _daily_forecast():
    """Run forecasts for all targets."""
    db = SessionLocal()
    try:
        targets = db.query(ForecastTarget).all()
        for target in targets:
            try:
                run = run_forecast(db, target.id, datetime.utcnow())
                logger.info("Forecast %s: run=%d status=%s", target.name, run.id, run.status)
            except Exception as e:
                logger.error("Forecast failed for %s: %s", target.name, e)
    finally:
        db.close()


async def _scheduler_loop():
    """Sleep until DAILY_HOUR_UTC, then run ingest + forecast daily."""
    while True:
        now = datetime.utcnow()
        # Calculate next run time
        next_run = now.replace(hour=DAILY_HOUR_UTC, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

        wait_seconds = (next_run - now).total_seconds()
        logger.info("Next daily run at %s UTC (in %.0f minutes)", next_run.isoformat(), wait_seconds / 60)

        await asyncio.sleep(wait_seconds)

        logger.info("=== Starting daily ingestion + forecast ===")
        try:
            await asyncio.get_event_loop().run_in_executor(None, _daily_ingest)
            await asyncio.get_event_loop().run_in_executor(None, _daily_forecast)
        except Exception as e:
            logger.error("Daily run failed: %s", e)


async def _backfill_and_schedule():
    """Background coroutine: backfill if needed, then start daily loop.

    Runs entirely in the background so the app can start serving
    immediately (critical for passing Railway's health check).
    """
    loop = asyncio.get_event_loop()
    try:
        did_backfill = await loop.run_in_executor(None, _backfill_if_empty)
        if did_backfill:
            logger.info("Running initial forecast after backfill...")
            await loop.run_in_executor(None, _daily_forecast)
    except Exception as e:
        logger.error("Backfill/initial forecast failed: %s", e)

    # Start the daily scheduler loop (runs forever)
    await _scheduler_loop()


async def start_scheduler():
    """Entry point called from FastAPI lifespan.

    Kicks off backfill + daily loop as a fire-and-forget task so the
    lifespan yields immediately and the app passes health checks.
    """
    asyncio.create_task(_backfill_and_schedule())
