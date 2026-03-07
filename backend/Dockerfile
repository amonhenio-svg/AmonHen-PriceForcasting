FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run seed (best-effort) then start server on Railway's dynamic PORT
CMD ["sh", "-c", "python seed_germany_pilot.py || echo 'Seed failed, continuing...'; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
