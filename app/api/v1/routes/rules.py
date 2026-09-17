"""Rule metadata endpoint — serves the static masking-rule definitions."""

from fastapi import APIRouter

from app.schemas.rule import RuleList
from app.services.rule_service import get_rules

router = APIRouter(tags=["rules"])


@router.get("/rules", response_model=RuleList, summary="List masking rules")
def list_rules() -> RuleList:
    return get_rules()
