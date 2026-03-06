from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func

from app.database import Base


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id = Column(Integer, primary_key=True, index=True)
    forecast_target_id = Column(Integer, ForeignKey("forecast_targets.id"), nullable=False)
    run_timestamp = Column(DateTime, nullable=False, server_default=func.now())
    model_version = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, running, completed, failed
    metrics_json = Column(Text, nullable=True)  # MAE, RMSE, etc.


class ForecastResult(Base):
    __tablename__ = "forecast_results"

    id = Column(Integer, primary_key=True, index=True)
    forecast_run_id = Column(Integer, ForeignKey("forecast_runs.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    value = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=True)
    upper_bound = Column(Float, nullable=True)
