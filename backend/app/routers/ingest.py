"""Data ingestion router - trigger data fetches from external sources."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.data.pipeline import fetch_and_store
from app.models import SeriesDefinition

router = APIRouter(prefix="/api/ingest", tags=["data ingestion"])


class IngestResponse(BaseModel):
    series_id: int
    series_name: str
    new_points: int


class BulkIngestResponse(BaseModel):
    results: list[IngestResponse]
    total_new_points: int


@router.post("/series/{series_id}", response_model=IngestResponse)
def ingest_series(
    series_id: int,
    start: datetime = Query(..., description="Start datetime (ISO 8601)"),
    end: datetime = Query(..., description="End datetime (ISO 8601)"),
    db: Session = Depends(get_db),
):
    """Trigger data fetch for a single series."""
    series = db.query(SeriesDefinition).filter(SeriesDefinition.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    try:
        count = fetch_and_store(db, series, start, end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Data source error: {e}")

    return IngestResponse(
        series_id=series.id,
        series_name=series.name,
        new_points=count,
    )


@router.post("/market/{market_id}", response_model=BulkIngestResponse)
def ingest_market(
    market_id: int,
    start: datetime = Query(..., description="Start datetime (ISO 8601)"),
    end: datetime = Query(..., description="End datetime (ISO 8601)"),
    db: Session = Depends(get_db),
):
    """Trigger data fetch for all series belonging to a market."""
    series_list = (
        db.query(SeriesDefinition)
        .filter(SeriesDefinition.market_id == market_id)
        .all()
    )
    if not series_list:
        raise HTTPException(status_code=404, detail="No series found for market")

    results = []
    for series in series_list:
        try:
            count = fetch_and_store(db, series, start, end)
            results.append(IngestResponse(
                series_id=series.id,
                series_name=series.name,
                new_points=count,
            ))
        except Exception as e:
            results.append(IngestResponse(
                series_id=series.id,
                series_name=f"{series.name} (ERROR: {e})",
                new_points=0,
            ))

    return BulkIngestResponse(
        results=results,
        total_new_points=sum(r.new_points for r in results),
    )


@router.post("/all", response_model=BulkIngestResponse)
def ingest_all(
    start: datetime = Query(..., description="Start datetime (ISO 8601)"),
    end: datetime = Query(..., description="End datetime (ISO 8601)"),
    db: Session = Depends(get_db),
):
    """Trigger data fetch for ALL series (including cross-market commodities)."""
    series_list = db.query(SeriesDefinition).all()
    if not series_list:
        raise HTTPException(status_code=404, detail="No series definitions found")

    results = []
    for series in series_list:
        try:
            count = fetch_and_store(db, series, start, end)
            results.append(IngestResponse(
                series_id=series.id,
                series_name=series.name,
                new_points=count,
            ))
        except Exception as e:
            results.append(IngestResponse(
                series_id=series.id,
                series_name=f"{series.name} (ERROR: {e})",
                new_points=0,
            ))

    return BulkIngestResponse(
        results=results,
        total_new_points=sum(r.new_points for r in results),
    )
