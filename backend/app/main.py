import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import markets, prices, data_sources, series, forecasts, ingest, dashboard

import logging as _logging

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    _logging.warning(f"Could not create tables on startup: {e}")

# Auto-seed default market and series definitions
try:
    from app.seed import seed
    seed()
except Exception as e:
    _logging.warning(f"Could not run seed on startup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background scheduler on app startup."""
    enable_scheduler = os.environ.get("ENABLE_SCHEDULER", "true").lower() in ("1", "true", "yes")
    if enable_scheduler:
        from app.scheduler import start_scheduler
        await start_scheduler()
        _logging.info("Background scheduler started")
    else:
        _logging.info("Scheduler disabled (ENABLE_SCHEDULER=%s)", os.environ.get("ENABLE_SCHEDULER"))
    yield


app = FastAPI(
    title="AmonHen Price Forecasting",
    description="Price forecasting API for European energy markets",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: comma-separated origins via env var; defaults to permissive for initial setup
cors_env = os.environ.get("CORS_ORIGINS", "")
allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()] if cors_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True if "*" not in allowed_origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(markets.router)
app.include_router(prices.router)
app.include_router(data_sources.router)
app.include_router(series.router)
app.include_router(forecasts.router)
app.include_router(ingest.router)
app.include_router(dashboard.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# In production, serve the built React frontend as static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    from fastapi.responses import FileResponse

    # Serve static assets (JS, CSS, images)
    app.mount("/static", StaticFiles(directory=os.path.join(static_dir, "static")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html for client-side routing."""
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))
