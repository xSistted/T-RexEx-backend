"""Pydantic models describing the request/response shapes for masking."""

from pydantic import BaseModel, Field
from typing import Dict

class MaskRequest(BaseModel):
    text: str = Field(..., max_length=50000)
    enabled_rules: list[str] | None = None
    include_matches: bool = True


class MaskMatch(BaseModel):
    rule_id: str
    label: str
    start: int
    end: int
    masked_value: str | None = None

class MaskSummary(BaseModel):
    total: int
    by_type: Dict[str, int]


class MaskResponse(BaseModel):
    masked_text: str
    summary: MaskSummary
    matches: list[MaskMatch] | None = None
    processing_time_ms: float
