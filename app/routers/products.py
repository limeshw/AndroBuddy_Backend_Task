from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductResponse

router = APIRouter(prefix="/products", tags=["Products (Catalog Stand-in)"])


@router.get("", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    """List stand-in catalog products for test exploration and verification."""
    return db.query(Product).filter(Product.is_active == True).all()

