from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import markets, prices, data_sources, series, forecasts

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AmonHen Price Forecasting",
    description="Price forecasting API for European energy markets",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(markets.router)
app.include_router(prices.router)
app.include_router(data_sources.router)
app.include_router(series.router)
app.include_router(forecasts.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
