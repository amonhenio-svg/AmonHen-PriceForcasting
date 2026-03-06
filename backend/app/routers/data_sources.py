from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DataSource
from app.schemas import DataSourceCreate, DataSourceResponse

router = APIRouter(prefix="/api/data-sources", tags=["data sources"])


@router.get("/", response_model=list[DataSourceResponse])
def list_data_sources(db: Session = Depends(get_db)):
    return db.query(DataSource).all()


@router.post("/", response_model=DataSourceResponse, status_code=201)
def create_data_source(source: DataSourceCreate, db: Session = Depends(get_db)):
    existing = db.query(DataSource).filter(DataSource.name == source.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Data source already exists")
    db_source = DataSource(**source.model_dump())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source
