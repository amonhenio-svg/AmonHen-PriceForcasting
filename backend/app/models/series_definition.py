from sqlalchemy import Column, ForeignKey, Integer, String

from app.database import Base


class SeriesDefinition(Base):
    __tablename__ = "series_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=False)  # price, load, generation, weather, commodity
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=True)  # null for cross-market series
    unit = Column(String, nullable=False)  # EUR/MWh, MW, °C, etc.
    granularity_minutes = Column(Integer, nullable=False, default=60)
    source_series_key = Column(String, nullable=True)  # identifier used by the external API
