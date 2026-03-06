from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    price = Column(Float, nullable=False)

    market = relationship("Market", back_populates="prices")
