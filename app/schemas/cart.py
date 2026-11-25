from typing import List
from pydantic import BaseModel, Field, ConfigDict


class CartItemCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="ID of the active product to add")
    quantity: int = Field(..., gt=0, description="Quantity must be at least 1")


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1, description="Updated quantity must be 1 or more")


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    unit_price: float
    quantity: int
    line_total: float

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    total_amount: float

    model_config = ConfigDict(from_attributes=True)

