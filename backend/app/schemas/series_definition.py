from pydantic import BaseModel


class SeriesDefinitionCreate(BaseModel):
    name: str
    category: str  # price, load, generation, weather, commodity
    data_source_id: int
    market_id: int | None = None
    unit: str
    granularity_minutes: int = 60
    source_series_key: str | None = None


class SeriesDefinitionResponse(BaseModel):
    id: int
    name: str
    category: str
    data_source_id: int
    market_id: int | None
    unit: str
    granularity_minutes: int
    source_series_key: str | None

    model_config = {"from_attributes": True}
