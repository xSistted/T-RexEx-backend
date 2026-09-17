"""Pydantic models describing the masking rule metadata responses."""

from pydantic import BaseModel, Field


class Rule(BaseModel):
    """Metadata for a single masking rule, rendered by the frontend panel."""

    id: str = Field(..., examples=["credit_card"])
    label_th: str = Field(..., examples=["เลขบัตรเครดิต"])
    label_en: str = Field(..., examples=["Credit Card"])
    pattern: str = Field(..., examples=[r"(?<![0-9-])[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}(?![0-9-])"])
    example_before: str = Field(..., examples=["1234-5678-9012-3456"])
    example_after: str = Field(..., examples=["XXXX-XXXX-XXXX-3456"])
    description: str = Field(..., examples=["เก็บเฉพาะ 4 ตัวท้าย"])


class RuleList(BaseModel):
    """Envelope returned by ``GET /rules``."""

    rules: list[Rule]
