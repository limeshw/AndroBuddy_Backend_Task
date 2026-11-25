from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class OrderCreate(BaseModel):
    shipping_address: str = Field(..., min_length=5, description="Full shipping delivery address")


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., description="Target order status: pending, paid, shipped, delivered, or cancelled")


class OrderItemResponse(BaseModel):
    id: int
    product_id: Optional[int]
    product_name: str
    unit_price: float
    quantity: int
    line_total: float

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: float
    shipping_address: str
    created_at: datetime
    items: List[OrderItemResponse]

    model_config = ConfigDict(from_attributes=True)


class PaginatedOrderResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[OrderResponse]

    model_config = ConfigDict(from_attributes=True)

