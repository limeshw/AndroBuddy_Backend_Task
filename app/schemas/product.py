from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    stock_quantity: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

