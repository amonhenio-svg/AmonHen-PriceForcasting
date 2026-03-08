from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ForecastTarget, ForecastRun, ForecastResult
from app.schemas import (
    ForecastTargetCreate,
    ForecastTargetResponse,
    ForecastRunResponse,
    ForecastResultResponse,
)

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])


class RunForecastRequest(BaseModel):
    forecast_start: datetime | None = None
    training_start: datetime | None = None


@router.get("/targets", response_model=list[ForecastTargetResponse])
def list_forecast_targets(
    market_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(ForecastTarget)
    if market_id:
        query = query.filter(ForecastTarget.market_id == market_id)
    return query.all()


@router.post("/targets", response_model=ForecastTargetResponse, status_code=201)
def create_forecast_target(target: ForecastTargetCreate, db: Session = Depends(get_db)):
    existing = db.query(ForecastTarget).filter(ForecastTarget.name == target.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Forecast target already exists")
    db_target = ForecastTarget(**target.model_dump())
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    return db_target


@router.get("/runs", response_model=list[ForecastRunResponse])
def list_forecast_runs(
    forecast_target_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_target_id == forecast_target_id)
        .order_by(ForecastRun.run_timestamp.desc())
        .all()
    )


@router.get("/results", response_model=list[ForecastResultResponse])
def get_forecast_results(
    forecast_run_id: int,
    db: Session = Depends(get_db),
):
    run = db.query(ForecastRun).filter(ForecastRun.id == forecast_run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    return (
        db.query(ForecastResult)
        .filter(ForecastResult.forecast_run_id == forecast_run_id)
        .order_by(ForecastResult.timestamp)
        .all()
    )


@router.post("/run/{target_id}", response_model=ForecastRunResponse)
def trigger_forecast_run(
    target_id: int,
    body: RunForecastRequest | None = None,
    db: Session = Depends(get_db),
):
    """Trigger a forecast run for a given target."""
    target = db.query(ForecastTarget).filter(ForecastTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Forecast target not found")

    from app.forecasting.pipeline import run_forecast

    forecast_start = (body.forecast_start if body and body.forecast_start else datetime.utcnow())
    training_start = body.training_start if body else None

    run = run_forecast(db, target_id, forecast_start, training_start)
    return run
