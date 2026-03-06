from datetime import datetime

from pydantic import BaseModel


class PriceCreate(BaseModel):
    market_id: int
    timestamp: datetime
    price: float


class PriceBulkCreate(BaseModel):
    prices: list[PriceCreate]


class PriceResponse(BaseModel):
    id: int
    market_id: int
    timestamp: datetime
    price: float

    model_config = {"from_attributes": True}
