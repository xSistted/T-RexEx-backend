from pydantic import BaseModel, Field
from typing import Dict

class DetectRequest(BaseModel):
    text: str = Field(..., max_length=50000)
    enabled_rules: list[str] | None = None
    include_matches: bool = True


class DetectMatch(BaseModel):
    rule_id: str
    label: str
    start: int
    end: int
    masked_value: str | None = None

class DetectSummary(BaseModel):
    total: int
    by_type: Dict[str, int]


class DetectResponse(BaseModel):
    summary: DetectSummary
    matches: list[DetectMatch] | None = None
    processing_time_ms: float
