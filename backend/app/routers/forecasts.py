from fastapi import APIRouter, Depends, HTTPException, Query
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
