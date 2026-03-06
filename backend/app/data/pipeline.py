"""Data pipeline for orchestrating data fetching and storage."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.data.sources.base import BaseDataSource
from app.data.sources.entsoe import EntsoeDataSource
from app.data.sources.open_meteo import OpenMeteoDataSource
from app.data.sources.commodity import CommodityDataSource
from app.models import DataSource, SeriesDefinition, TimeSeriesData


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


def fetch_and_store(
    db: Session,
    series_def: SeriesDefinition,
    start: datetime,
    end: datetime,
) -> int:
    """Fetch data for a series definition and store it in the database.

    Returns the number of new data points stored.
    """
    data_source = db.query(DataSource).filter(DataSource.id == series_def.data_source_id).first()
    if not data_source:
        raise ValueError(f"Data source not found for series {series_def.name}")

    source = get_source_instance(data_source)
    df = source.fetch(series_def.source_series_key, start, end)

    if df.empty:
        return 0

    count = 0
    for _, row in df.iterrows():
        existing = (
            db.query(TimeSeriesData)
            .filter(
                TimeSeriesData.series_id == series_def.id,
                TimeSeriesData.timestamp == row["timestamp"],
            )
            .first()
        )
        if not existing:
            db.add(TimeSeriesData(
                series_id=series_def.id,
                timestamp=row["timestamp"],
                value=row["value"],
            ))
            count += 1

    db.commit()
    return count
