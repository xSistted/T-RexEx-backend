"""Pydantic models for the data-masking endpoint."""

from pydantic import BaseModel, Field


class MaskRequest(BaseModel):
    """Text submitted by the client for masking."""

    text: str = Field(
        ...,
        min_length=1,
        examples=[
            "Card: 1234-5678-9012-3456 "
            "Email: somchai.d@company.com"
        ],
    )


class MaskResponse(BaseModel):
    """Masked text returned to the client."""

    masked_text: str