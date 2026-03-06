from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    country = Column(String, nullable=False)
    commodity = Column(String, nullable=False)  # e.g. "electricity", "gas"
    currency = Column(String, default="EUR")
    unit = Column(String, default="MWh")  # price unit, e.g. EUR/MWh

    prices = relationship("Price", back_populates="market")
