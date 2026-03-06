from pydantic import BaseModel


class MarketCreate(BaseModel):
    name: str
    country: str
    commodity: str
    currency: str = "EUR"
    unit: str = "MWh"


class MarketResponse(BaseModel):
    id: int
    name: str
    country: str
    commodity: str
    currency: str
    unit: str

    model_config = {"from_attributes": True}
