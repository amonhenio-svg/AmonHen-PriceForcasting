#!/bin/sh
set -e

# Start the API server — the scheduler handles backfill + daily ingestion
# in the background after the app starts serving requests
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
