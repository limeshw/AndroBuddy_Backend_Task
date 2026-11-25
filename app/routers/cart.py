from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import require_customer
from app.models.user import User
from app.schemas.cart import CartResponse, CartItemCreate, CartItemUpdate
from app.services.cart_service import cart_service

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=CartResponse)
def get_cart(
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    cart = cart_service.get_or_create_cart(db, current_user)
    return cart_service.format_cart_response(cart)


@router.post("/items", response_model=CartResponse, status_code=status.HTTP_200_OK)
def add_item_to_cart(
    data: CartItemCreate,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    return cart_service.add_item_to_cart(db, current_user, data)


@router.patch("/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    item_id: int,
    data: CartItemUpdate,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    return cart_service.update_cart_item(db, current_user, item_id, data)


@router.delete("/items/{item_id}", response_model=CartResponse)
def remove_cart_item(
    item_id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    return cart_service.remove_cart_item(db, current_user, item_id)


@router.delete("", status_code=status.HTTP_200_OK)
def empty_cart(
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    return cart_service.empty_cart(db, current_user)

