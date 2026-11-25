from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import require_customer, require_admin
from app.models.user import User
from app.schemas.order import OrderCreate, OrderStatusUpdate, OrderResponse, PaginatedOrderResponse
from app.services.order_service import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def checkout_order(
    data: OrderCreate,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Checkout current customer's cart:
    - Atomically checks stock, deducts quantity, creates order with price snapshots, and empties cart.
    - Returns 409 if cart is empty or stock is insufficient.
    """
    return order_service.checkout(db, current_user, data)


@router.get("", response_model=PaginatedOrderResponse)
def get_my_orders(
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(10, ge=1, le=100, description="Page limit"),
    status: Optional[str] = Query(None, description="Optional filter by status"),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """Retrieve caller's orders, newest first, paginated. Supports status filter (bonus)."""
    return order_service.get_user_orders(db, current_user, skip=skip, limit=limit, order_status=status)


@router.get("/{id}", response_model=OrderResponse)
def get_order_details(
    id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Get details of one order.
    Returns 404 if the order does not exist or belongs to another customer.
    """
    return order_service.get_order_by_id(db, current_user, id)


@router.post("/{id}/cancel", response_model=OrderResponse)
def cancel_order(
    id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Cancel an order (customer only).
    Can only cancel while status is 'pending'. Restores product stock.
    """
    return order_service.cancel_order(db, current_user, id)


@router.patch("/{id}/status", response_model=OrderResponse)
def update_order_status(
    id: int,
    data: OrderStatusUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Admin only: Advance or cancel order status through allowed state machine.
    Returns 409 on disallowed status transitions.
    """
    return order_service.update_order_status_admin(db, id, data.status)

