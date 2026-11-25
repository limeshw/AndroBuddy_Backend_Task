from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.user import User
from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.order import OrderCreate, OrderStatusUpdate, OrderResponse, OrderItemResponse, PaginatedOrderResponse
from app.core.dependencies import check_order_ownership


class OrderService:
    @staticmethod
    def format_order_response(order: Order) -> OrderResponse:
        item_responses = [
            OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product_name,
                unit_price=item.unit_price,
                quantity=item.quantity,
                line_total=round(item.unit_price * item.quantity, 2),
            )
            for item in order.items
        ]
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            total_amount=round(order.total_amount, 2),
            shipping_address=order.shipping_address,
            created_at=order.created_at,
            items=item_responses,
        )

    @staticmethod
    def checkout(db: Session, user: User, data: OrderCreate) -> OrderResponse:
        """
        Atomic checkout transaction:
        1. Ensure cart has items.
        2. Re-check stock for every item. Fail with 409 if any item is short.
        3. Snapshot name and price into OrderItem.
        4. Decrement stock, create order and order items, empty cart in one transaction.
        Rolls back completely on failure.
        """
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()
        if not cart or not cart.items:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot checkout: cart is empty",
            )

        # Re-check stock for each item and collect all offending items
        insufficient_stock_errors = []
        for item in cart.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product or not product.is_active:
                insufficient_stock_errors.append(
                    f"Product '{item.product.name if item.product else item.product_id}' is no longer active or available"
                )
            elif product.stock_quantity < item.quantity:
                insufficient_stock_errors.append(
                    f"'{product.name}': requested {item.quantity}, but only {product.stock_quantity} available"
                )

        if insufficient_stock_errors:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock check failed for items: {'; '.join(insufficient_stock_errors)}",
            )

        try:
            # Calculate total and build snapshot items
            total_amount = 0.0
            order_items_to_create = []

            for item in cart.items:
                product = db.query(Product).filter(Product.id == item.product_id).first()
                # Deduct stock
                product.stock_quantity -= item.quantity

                item_line_total = product.price * item.quantity
                total_amount += item_line_total

                order_item = OrderItem(
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=item.quantity,
                )
                order_items_to_create.append(order_item)

            # Create Order
            order = Order(
                user_id=user.id,
                status=OrderStatus.PENDING,
                total_amount=round(total_amount, 2),
                shipping_address=data.shipping_address.strip(),
                items=order_items_to_create,
            )
            db.add(order)

            # Empty Cart
            db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

            db.commit()
            db.refresh(order)
            return OrderService.format_order_response(order)

        except Exception as e:
            db.rollback()
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred during checkout: {str(e)}",
            )

    @staticmethod
    def get_user_orders(
        db: Session,
        user: User,
        skip: int = 0,
        limit: int = 10,
        order_status: Optional[str] = None,
    ) -> PaginatedOrderResponse:
        query = db.query(Order).filter(Order.user_id == user.id)

        if order_status:
            query = query.filter(Order.status == order_status.lower())

        total = query.count()
        orders = (
            query.order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        page = (skip // limit) + 1 if limit > 0 else 1
        return PaginatedOrderResponse(
            total=total,
            page=page,
            limit=limit,
            items=[OrderService.format_order_response(o) for o in orders],
        )

    @staticmethod
    def get_order_by_id(db: Session, user: User, order_id: int) -> OrderResponse:
        order = db.query(Order).filter(Order.id == order_id).first()
        # Ownership check: if order belongs to another customer or doesn't exist, return 404
        verified_order = check_order_ownership(order, user)
        return OrderService.format_order_response(verified_order)

    @staticmethod
    def cancel_order(db: Session, user: User, order_id: int) -> OrderResponse:
        """
        Customer can cancel ONLY while status is 'pending'.
        Cancelling restores the inventory stock.
        """
        order = db.query(Order).filter(Order.id == order_id).first()
        verified_order = check_order_ownership(order, user)

        if verified_order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot cancel order with status '{verified_order.status}'. Only 'pending' orders can be cancelled by customer.",
            )

        try:
            # Restore stock for each item in the order
            for item in verified_order.items:
                if item.product_id:
                    product = db.query(Product).filter(Product.id == item.product_id).first()
                    if product:
                        product.stock_quantity += item.quantity

            verified_order.status = OrderStatus.CANCELLED
            db.commit()
            db.refresh(verified_order)
            return OrderService.format_order_response(verified_order)

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel order: {str(e)}",
            )

    @staticmethod
    def update_order_status_admin(db: Session, order_id: int, target_status: str) -> OrderResponse:
        """
        Admin only status update.
        Allowed state machine:
          pending -> paid -> shipped -> delivered
          pending or paid -> cancelled
        Cancelling also restores stock!
        Any invalid transition returns 409.
        """
        target = target_status.lower().strip()
        all_valid_statuses = [
            OrderStatus.PENDING,
            OrderStatus.PAID,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
        ]
        if target not in all_valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{target_status}'. Valid statuses: {all_valid_statuses}",
            )

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_id} not found",
            )

        current = order.status
        allowed = OrderStatus.ALLOWED_TRANSITIONS.get(current, [])

        if target not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invalid status transition from '{current}' to '{target}'. Allowed transitions: {allowed}",
            )

        try:
            # If moving to cancelled, restore stock
            if target == OrderStatus.CANCELLED:
                for item in order.items:
                    if item.product_id:
                        product = db.query(Product).filter(Product.id == item.product_id).first()
                        if product:
                            product.stock_quantity += item.quantity

            order.status = target
            db.commit()
            db.refresh(order)
            return OrderService.format_order_response(order)

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update order status: {str(e)}",
            )


order_service = OrderService()

