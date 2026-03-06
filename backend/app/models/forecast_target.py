from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.database import Base


class ForecastTarget(Base):
    __tablename__ = "forecast_targets"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    name = Column(String, unique=True, nullable=False)
    horizon_hours = Column(Integer, nullable=False)  # how far ahead to forecast
    granularity_minutes = Column(Integer, nullable=False, default=60)
    model_config_json = Column(Text, nullable=True)  # models, features, ensemble weights
