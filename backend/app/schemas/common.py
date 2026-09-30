"""Shared schema helpers."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class PaginationParams(BaseModel):
    limit: Annotated[int, Field(ge=1, le=100)] = 20
    offset: Annotated[int, Field(ge=0)] = 0


class Page(BaseModel):
    """Envelope for list responses."""

    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + self.limit < self.total


class TimestampedSchema(ORMModel):
    created_at: datetime
    updated_at: datetime


Money = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
