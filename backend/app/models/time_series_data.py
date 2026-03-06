from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, UniqueConstraint

from app.database import Base


class TimeSeriesData(Base):
    __tablename__ = "time_series_data"

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey("series_definitions.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    value = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("series_id", "timestamp", name="uq_series_timestamp"),
    )
