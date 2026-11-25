from typing import Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartResponse, CartItemResponse


class CartService:
    @staticmethod
    def get_or_create_cart(db: Session, user: User) -> Cart:
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()
        if not cart:
            cart = Cart(user_id=user.id)
            db.add(cart)
            db.commit()
            db.refresh(cart)
        return cart

    @staticmethod
    def format_cart_response(cart: Cart) -> CartResponse:
        item_responses = []
        cart_total = 0.0

        for item in cart.items:
            unit_price = item.product.price if item.product else 0.0
            product_name = item.product.name if item.product else "Unknown Product"
            line_total = round(unit_price * item.quantity, 2)
            cart_total += line_total

            item_responses.append(
                CartItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    product_name=product_name,
                    unit_price=unit_price,
                    quantity=item.quantity,
                    line_total=line_total,
                )
            )

        return CartResponse(
            id=cart.id,
            items=item_responses,
            total_amount=round(cart_total, 2),
        )

    @staticmethod
    def add_item_to_cart(db: Session, user: User, data: CartItemCreate) -> CartResponse:
        cart = CartService.get_or_create_cart(db, user)

        # 1. Product must exist and be active
        product = db.query(Product).filter(Product.id == data.product_id).first()
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {data.product_id} is either inactive or does not exist",
            )

        # 2. Check existing item in cart
        existing_item = (
            db.query(CartItem)
            .filter(CartItem.cart_id == cart.id, CartItem.product_id == data.product_id)
            .first()
        )

        desired_quantity = data.quantity
        if existing_item:
            desired_quantity += existing_item.quantity

        # 3. Requested quantity cannot exceed stock (409)
        if desired_quantity > product.stock_quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Requested quantity {desired_quantity} exceeds available stock ({product.stock_quantity}) for '{product.name}'",
            )

        if existing_item:
            existing_item.quantity = desired_quantity
        else:
            new_item = CartItem(
                cart_id=cart.id,
                product_id=product.id,
                quantity=data.quantity,
            )
            db.add(new_item)

        db.commit()
        db.refresh(cart)
        return CartService.format_cart_response(cart)

    @staticmethod
    def update_cart_item(db: Session, user: User, item_id: int, data: CartItemUpdate) -> CartResponse:
        cart = CartService.get_or_create_cart(db, user)

        item = (
            db.query(CartItem)
            .filter(CartItem.id == item_id, CartItem.cart_id == cart.id)
            .first()
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cart item {item_id} not found in caller's cart",
            )

        product = item.product
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product associated with this cart item is no longer active",
            )

        if data.quantity > product.stock_quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Requested quantity {data.quantity} exceeds available stock ({product.stock_quantity}) for '{product.name}'",
            )

        item.quantity = data.quantity
        db.commit()
        db.refresh(cart)
        return CartService.format_cart_response(cart)

    @staticmethod
    def remove_cart_item(db: Session, user: User, item_id: int) -> CartResponse:
        cart = CartService.get_or_create_cart(db, user)

        item = (
            db.query(CartItem)
            .filter(CartItem.id == item_id, CartItem.cart_id == cart.id)
            .first()
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cart item {item_id} not found in caller's cart",
            )

        db.delete(item)
        db.commit()
        db.refresh(cart)
        return CartService.format_cart_response(cart)

    @staticmethod
    def empty_cart(db: Session, user: User) -> dict:
        cart = CartService.get_or_create_cart(db, user)
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        db.commit()
        return {"detail": "Cart emptied successfully"}


cart_service = CartService()

