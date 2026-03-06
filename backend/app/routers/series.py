from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SeriesDefinition
from app.schemas import SeriesDefinitionCreate, SeriesDefinitionResponse

router = APIRouter(prefix="/api/series", tags=["series definitions"])


@router.get("/", response_model=list[SeriesDefinitionResponse])
def list_series(
    category: str | None = Query(None),
    market_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(SeriesDefinition)
    if category:
        query = query.filter(SeriesDefinition.category == category)
    if market_id:
        query = query.filter(SeriesDefinition.market_id == market_id)
    return query.all()


@router.post("/", response_model=SeriesDefinitionResponse, status_code=201)
def create_series(series: SeriesDefinitionCreate, db: Session = Depends(get_db)):
    existing = db.query(SeriesDefinition).filter(SeriesDefinition.name == series.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Series already exists")
    db_series = SeriesDefinition(**series.model_dump())
    db.add(db_series)
    db.commit()
    db.refresh(db_series)
    return db_series


@router.get("/{series_id}", response_model=SeriesDefinitionResponse)
def get_series(series_id: int, db: Session = Depends(get_db)):
    series = db.query(SeriesDefinition).filter(SeriesDefinition.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    return series
