import json
from functools import lru_cache
from pathlib import Path

from app.schemas.rule import RuleList

_RULES_FILE = Path(__file__).resolve().parent.parent / "data" / "rules.json"


@lru_cache
def get_rules() -> RuleList:

    with _RULES_FILE.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return RuleList.model_validate(data)
