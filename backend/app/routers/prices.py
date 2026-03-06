from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SeriesDefinition, TimeSeriesData
from app.schemas import TimeSeriesDataBulkCreate, TimeSeriesDataCreate, TimeSeriesDataResponse

router = APIRouter(prefix="/api/timeseries", tags=["time series"])


@router.get("/", response_model=list[TimeSeriesDataResponse])
def list_timeseries(
    series_id: int,
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    db: Session = Depends(get_db),
):
    series = db.query(SeriesDefinition).filter(SeriesDefinition.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    query = db.query(TimeSeriesData).filter(TimeSeriesData.series_id == series_id)
    if start:
        query = query.filter(TimeSeriesData.timestamp >= start)
    if end:
        query = query.filter(TimeSeriesData.timestamp <= end)
    return query.order_by(TimeSeriesData.timestamp).all()


@router.post("/", response_model=TimeSeriesDataResponse, status_code=201)
def create_timeseries_point(data: TimeSeriesDataCreate, db: Session = Depends(get_db)):
    series = db.query(SeriesDefinition).filter(SeriesDefinition.id == data.series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    db_data = TimeSeriesData(**data.model_dump())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data


@router.post("/bulk", response_model=list[TimeSeriesDataResponse], status_code=201)
def create_timeseries_bulk(data: TimeSeriesDataBulkCreate, db: Session = Depends(get_db)):
    db_records = [TimeSeriesData(**d.model_dump()) for d in data.data]
    db.add_all(db_records)
    db.commit()
    for r in db_records:
        db.refresh(r)
    return db_records
