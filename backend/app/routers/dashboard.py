"""Dashboard summary and analytics endpoints."""

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Market, SeriesDefinition, TimeSeriesData,
    ForecastTarget, ForecastRun, ForecastResult,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class LatestPrice(BaseModel):
    series_id: int
    series_name: str
    category: str
    unit: str
    latest_value: float | None
    latest_timestamp: datetime | None
    change_24h: float | None  # percentage change


class ForecastSummary(BaseModel):
    target_id: int
    target_name: str
    horizon_hours: int
    latest_run_id: int | None
    latest_run_status: str | None
    latest_run_time: datetime | None
    metrics: dict | None


class DataStatus(BaseModel):
    series_id: int
    series_name: str
    category: str
    total_points: int
    latest_timestamp: datetime | None
    freshness_hours: float | None  # hours since last data point


class DashboardSummaryResponse(BaseModel):
    market: dict
    latest_prices: list[LatestPrice]
    forecasts: list[ForecastSummary]
    data_status: list[DataStatus]


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    market_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Single endpoint for full dashboard overview."""
    market = db.query(Market).filter(Market.id == market_id).first()
    market_dict = {
        "id": market.id, "name": market.name, "country": market.country,
        "currency": market.currency, "unit": market.unit,
    } if market else {}

    # Latest prices for all series in this market + cross-market commodities
    series_list = db.query(SeriesDefinition).filter(
        (SeriesDefinition.market_id == market_id) |
        (SeriesDefinition.market_id.is_(None))
    ).all()

    now = datetime.utcnow()
    latest_prices = []
    data_status = []

    for s in series_list:
        # Latest value
        latest = (
            db.query(TimeSeriesData)
            .filter(TimeSeriesData.series_id == s.id)
            .order_by(desc(TimeSeriesData.timestamp))
            .first()
        )

        # 24h ago value for change calculation
        change_24h = None
        if latest:
            prev = (
                db.query(TimeSeriesData)
                .filter(
                    TimeSeriesData.series_id == s.id,
                    TimeSeriesData.timestamp <= latest.timestamp - timedelta(hours=24),
                )
                .order_by(desc(TimeSeriesData.timestamp))
                .first()
            )
            if prev and prev.value != 0:
                change_24h = round((latest.value - prev.value) / abs(prev.value) * 100, 2)

        latest_prices.append(LatestPrice(
            series_id=s.id,
            series_name=s.name,
            category=s.category,
            unit=s.unit,
            latest_value=round(latest.value, 2) if latest else None,
            latest_timestamp=latest.timestamp if latest else None,
            change_24h=change_24h,
        ))

        # Data freshness
        total = db.query(func.count(TimeSeriesData.id)).filter(
            TimeSeriesData.series_id == s.id
        ).scalar()

        freshness = None
        if latest:
            freshness = round((now - latest.timestamp).total_seconds() / 3600, 1)

        data_status.append(DataStatus(
            series_id=s.id,
            series_name=s.name,
            category=s.category,
            total_points=total,
            latest_timestamp=latest.timestamp if latest else None,
            freshness_hours=freshness,
        ))

    # Forecast summaries
    targets = db.query(ForecastTarget).filter(
        ForecastTarget.market_id == market_id
    ).all()

    forecasts = []
    for t in targets:
        latest_run = (
            db.query(ForecastRun)
            .filter(ForecastRun.forecast_target_id == t.id)
            .order_by(desc(ForecastRun.run_timestamp))
            .first()
        )

        metrics = None
        if latest_run and latest_run.metrics_json:
            try:
                metrics = json.loads(latest_run.metrics_json)
            except (json.JSONDecodeError, TypeError):
                pass

        forecasts.append(ForecastSummary(
            target_id=t.id,
            target_name=t.name,
            horizon_hours=t.horizon_hours,
            latest_run_id=latest_run.id if latest_run else None,
            latest_run_status=latest_run.status if latest_run else None,
            latest_run_time=latest_run.run_timestamp if latest_run else None,
            metrics=metrics,
        ))

    return DashboardSummaryResponse(
        market=market_dict,
        latest_prices=latest_prices,
        forecasts=forecasts,
        data_status=data_status,
    )


class AccuracyPoint(BaseModel):
    timestamp: datetime
    actual: float
    forecast: float
    error: float  # actual - forecast


class AccuracyResponse(BaseModel):
    forecast_run_id: int
    target_name: str
    mae: float | None
    rmse: float | None
    mape: float | None
    points: list[AccuracyPoint]


@router.get("/accuracy", response_model=AccuracyResponse)
def forecast_accuracy(
    forecast_run_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Compare forecast results against actual values for a given run."""
    run = db.query(ForecastRun).filter(ForecastRun.id == forecast_run_id).first()
    if not run:
        from fastapi import HTTPException
        raise HTTPException(404, "Forecast run not found")

    target = db.query(ForecastTarget).filter(
        ForecastTarget.id == run.forecast_target_id
    ).first()

    config = json.loads(target.model_config_json) if target and target.model_config_json else {}
    target_series_id = config.get("target_series_id")

    # Get forecast results
    results = (
        db.query(ForecastResult)
        .filter(ForecastResult.forecast_run_id == forecast_run_id)
        .order_by(ForecastResult.timestamp)
        .all()
    )

    if not results or not target_series_id:
        return AccuracyResponse(
            forecast_run_id=forecast_run_id,
            target_name=target.name if target else "Unknown",
            mae=None, rmse=None, mape=None, points=[],
        )

    # Get actual values for the same timestamps
    forecast_timestamps = [r.timestamp for r in results]
    actuals = (
        db.query(TimeSeriesData)
        .filter(
            TimeSeriesData.series_id == target_series_id,
            TimeSeriesData.timestamp.in_(forecast_timestamps),
        )
        .all()
    )
    actual_map = {a.timestamp: a.value for a in actuals}

    # Build accuracy points
    points = []
    errors = []
    pct_errors = []
    for r in results:
        actual = actual_map.get(r.timestamp)
        if actual is not None:
            err = actual - r.value
            points.append(AccuracyPoint(
                timestamp=r.timestamp,
                actual=actual,
                forecast=r.value,
                error=round(err, 2),
            ))
            errors.append(err)
            if actual != 0:
                pct_errors.append(abs(err / actual) * 100)

    mae = round(sum(abs(e) for e in errors) / len(errors), 2) if errors else None
    rmse = round((sum(e**2 for e in errors) / len(errors)) ** 0.5, 2) if errors else None
    mape = round(sum(pct_errors) / len(pct_errors), 2) if pct_errors else None

    return AccuracyResponse(
        forecast_run_id=forecast_run_id,
        target_name=target.name if target else "Unknown",
        mae=mae,
        rmse=rmse,
        mape=mape,
        points=points,
    )
