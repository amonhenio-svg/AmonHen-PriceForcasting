from datetime import datetime

from pydantic import BaseModel


class ForecastTargetCreate(BaseModel):
    market_id: int
    name: str
    horizon_hours: int
    granularity_minutes: int = 60
    model_config_json: str | None = None


class ForecastTargetResponse(BaseModel):
    id: int
    market_id: int
    name: str
    horizon_hours: int
    granularity_minutes: int
    model_config_json: str | None

    model_config = {"from_attributes": True}


class ForecastRunResponse(BaseModel):
    id: int
    forecast_target_id: int
    run_timestamp: datetime
    model_version: str | None
    status: str
    metrics_json: str | None

    model_config = {"from_attributes": True}


class ForecastResultResponse(BaseModel):
    id: int
    forecast_run_id: int
    timestamp: datetime
    value: float
    lower_bound: float | None
    upper_bound: float | None

    model_config = {"from_attributes": True}
