"""Data pipeline for orchestrating data fetching and storage."""

import logging
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.data.sources.base import BaseDataSource
from app.data.sources.entsoe import EntsoeDataSource
from app.data.sources.open_meteo import OpenMeteoDataSource
from app.data.sources.commodity import CommodityDataSource
from app.models import DataSource, SeriesDefinition, TimeSeriesData

logger = logging.getLogger(__name__)

SOURCE_CLASSES = {
    "entsoe": EntsoeDataSource,
    "open_meteo": OpenMeteoDataSource,
    "commodity": CommodityDataSource,
}


def get_source_instance(data_source: DataSource) -> BaseDataSource:
    """Create a data source instance from a database record."""
    cls = SOURCE_CLASSES.get(data_source.source_type)
    if not cls:
        raise ValueError(f"Unknown source type: {data_source.source_type}")
    return cls()


def _is_postgresql(db: Session) -> bool:
    """Check if the database is PostgreSQL."""
    return "postgresql" in str(db.bind.url)


def _to_python_datetime(ts) -> datetime:
    """Convert pandas Timestamp (possibly tz-aware) to naive Python datetime."""
    if isinstance(ts, pd.Timestamp):
        if ts.tzinfo is not None:
            ts = ts.tz_convert("UTC").tz_localize(None)
        return ts.to_pydatetime()
    return ts


def _bulk_upsert_postgres(db: Session, series_id: int, df: pd.DataFrame) -> int:
    """Bulk upsert using PostgreSQL ON CONFLICT."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    rows = [
        {"series_id": series_id, "timestamp": _to_python_datetime(row["timestamp"]), "value": float(row["value"])}
        for _, row in df.iterrows()
    ]
    if not rows:
        return 0

    chunk_size = 1000
    total_inserted = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        stmt = pg_insert(TimeSeriesData).values(chunk)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_series_timestamp"
        )
        result = db.execute(stmt)
        total_inserted += result.rowcount

    db.commit()
    return total_inserted


def _bulk_upsert_sqlite(db: Session, series_id: int, df: pd.DataFrame) -> int:
    """Bulk insert for SQLite, skipping duplicates."""
    rows = [
        {"series_id": series_id, "timestamp": _to_python_datetime(row["timestamp"]), "value": float(row["value"])}
        for _, row in df.iterrows()
    ]
    if not rows:
        return 0

    chunk_size = 500
    total_inserted = 0
    stmt = text(
        "INSERT OR IGNORE INTO time_series_data (series_id, timestamp, value) "
        "VALUES (:series_id, :timestamp, :value)"
    )
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        for row in chunk:
            result = db.execute(stmt, row)
            total_inserted += result.rowcount

    db.commit()
    return total_inserted


def fetch_and_store(
    db: Session,
    series_def: SeriesDefinition,
    start: datetime,
    end: datetime,
) -> int:
    """Fetch data for a series definition and store it in the database.

    Automatically chunks long date ranges (ENTSO-E limits ~1 year per request).
    Uses bulk upsert for performance.

    Returns the number of new data points stored.
    """
    data_source = db.query(DataSource).filter(DataSource.id == series_def.data_source_id).first()
    if not data_source:
        raise ValueError(f"Data source not found for series {series_def.name}")

    source = get_source_instance(data_source)

    # Chunk long date ranges (ENTSO-E has limits on request duration)
    all_dfs = []
    chunk_start = start
    max_days = 365
    while chunk_start < end:
        chunk_end = min(
            chunk_start + pd.Timedelta(days=max_days),
            pd.Timestamp(end),
        )
        logger.info(
            "Fetching %s from %s to %s",
            series_def.source_series_key, chunk_start, chunk_end,
        )
        try:
            df = source.fetch(series_def.source_series_key, chunk_start, chunk_end)
            if not df.empty:
                all_dfs.append(df)
        except Exception as e:
            logger.error("Error fetching chunk %s-%s: %s", chunk_start, chunk_end, e)
        chunk_start = chunk_end

    if not all_dfs:
        return 0

    df = pd.concat(all_dfs, ignore_index=True)
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    logger.info("Total fetched: %d points for %s", len(df), series_def.name)

    # Bulk upsert based on database engine
    if _is_postgresql(db):
        count = _bulk_upsert_postgres(db, series_def.id, df)
    else:
        count = _bulk_upsert_sqlite(db, series_def.id, df)

    logger.info("Stored %d new points for %s", count, series_def.name)
    return count
