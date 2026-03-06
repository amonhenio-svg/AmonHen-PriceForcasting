from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Market
from app.schemas import MarketCreate, MarketResponse

router = APIRouter(prefix="/api/markets", tags=["markets"])


@router.get("/", response_model=list[MarketResponse])
def list_markets(db: Session = Depends(get_db)):
    return db.query(Market).all()


@router.post("/", response_model=MarketResponse, status_code=201)
def create_market(market: MarketCreate, db: Session = Depends(get_db)):
    existing = db.query(Market).filter(Market.name == market.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Market already exists")
    db_market = Market(**market.model_dump())
    db.add(db_market)
    db.commit()
    db.refresh(db_market)
    return db_market


@router.get("/{market_id}", response_model=MarketResponse)
def get_market(market_id: int, db: Session = Depends(get_db)):
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    return market
