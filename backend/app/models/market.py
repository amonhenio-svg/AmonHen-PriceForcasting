from sqlalchemy import Column, Integer, String

from app.database import Base


class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    country = Column(String, nullable=False)
    commodity = Column(String, nullable=False)  # electricity, gas
    market_type = Column(String, nullable=False)  # day_ahead, intraday, reserve
    timezone = Column(String, nullable=False, default="Europe/Berlin")
    granularity_minutes = Column(Integer, nullable=False, default=60)
    currency = Column(String, default="EUR")
    unit = Column(String, default="MWh")
