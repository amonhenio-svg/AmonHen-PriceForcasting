# AmonHen Price Forecasting

Price forecasting tool for European energy markets.

## Project Structure

```
├── backend/          # FastAPI Python backend
│   ├── app/
│   │   ├── models/   # SQLAlchemy database models
│   │   ├── routers/  # API route handlers
│   │   ├── schemas/  # Pydantic request/response schemas
│   │   └── services/ # Business logic and forecasting
│   └── requirements.txt
├── frontend/         # React JS frontend
└── README.md
```

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000 with docs at http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm start
```

The frontend will be available at http://localhost:3000
