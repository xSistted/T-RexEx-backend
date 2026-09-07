"""Pydantic models describing the request/response shapes for items."""

from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Sword"])
    description: str | None = Field(default=None, max_length=500)
    price: float = Field(..., ge=0, examples=[9.99])


class ItemCreate(ItemBase):
    """Payload for creating an item."""


class ItemUpdate(BaseModel):
    """Payload for partially updating an item (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float | None = Field(default=None, ge=0)


class ItemRead(ItemBase):
    """Item as returned to clients."""

    id: int
