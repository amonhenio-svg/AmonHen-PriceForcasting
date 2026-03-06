from pydantic import BaseModel


class MarketCreate(BaseModel):
    name: str
    country: str
    commodity: str
    market_type: str
    timezone: str = "Europe/Berlin"
    granularity_minutes: int = 60
    currency: str = "EUR"
    unit: str = "MWh"


class MarketResponse(BaseModel):
    id: int
    name: str
    country: str
    commodity: str
    market_type: str
    timezone: str
    granularity_minutes: int
    currency: str
    unit: str

    model_config = {"from_attributes": True}
