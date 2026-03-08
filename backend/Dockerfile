FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

ENV PORT=8000

# Start server on Railway's dynamic PORT
CMD ["sh", "-c", "python -c 'from app.main import app; print(\"App imported OK\")' && (timeout 15 python seed_germany_pilot.py || echo 'Seed skipped') && exec uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
