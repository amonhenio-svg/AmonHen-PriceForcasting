#!/bin/sh
set -e

# Best-effort seed
timeout 15 python seed_germany_pilot.py || echo "Seed skipped"

# Start the API server
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
