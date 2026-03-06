from datetime import datetime

from pydantic import BaseModel


class TimeSeriesDataCreate(BaseModel):
    series_id: int
    timestamp: datetime
    value: float


class TimeSeriesDataBulkCreate(BaseModel):
    data: list[TimeSeriesDataCreate]


class TimeSeriesDataResponse(BaseModel):
    id: int
    series_id: int
    timestamp: datetime
    value: float

    model_config = {"from_attributes": True}
