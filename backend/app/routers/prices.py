from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Market, Price
from app.schemas import PriceBulkCreate, PriceCreate, PriceResponse

router = APIRouter(prefix="/api/prices", tags=["prices"])


@router.get("/", response_model=list[PriceResponse])
def list_prices(
    market_id: int,
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Price).filter(Price.market_id == market_id)
    if start:
        query = query.filter(Price.timestamp >= start)
    if end:
        query = query.filter(Price.timestamp <= end)
    return query.order_by(Price.timestamp).all()


@router.post("/", response_model=PriceResponse, status_code=201)
def create_price(price: PriceCreate, db: Session = Depends(get_db)):
    market = db.query(Market).filter(Market.id == price.market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    db_price = Price(**price.model_dump())
    db.add(db_price)
    db.commit()
    db.refresh(db_price)
    return db_price


@router.post("/bulk", response_model=list[PriceResponse], status_code=201)
def create_prices_bulk(data: PriceBulkCreate, db: Session = Depends(get_db)):
    db_prices = [Price(**p.model_dump()) for p in data.prices]
    db.add_all(db_prices)
    db.commit()
    for p in db_prices:
        db.refresh(p)
    return db_prices
