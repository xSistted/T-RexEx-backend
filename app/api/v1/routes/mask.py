"""Masking endpoint."""

import time
from collections import Counter
from fastapi import APIRouter

from app.schemas.mask import MaskRequest, MaskResponse, MaskSummary, MaskMatch
from app.services import masking_service
from app.services.masking_service import RULE_MODULES

router = APIRouter(tags=["mask"])


@router.post("/mask", summary="mask data", response_model=MaskResponse)
def mask(request: MaskRequest) -> MaskResponse:
    start_time = time.perf_counter()
    detections = masking_service.detect(request.text, request.enabled_rules)
    return MaskResponse(
        masked_text=masking_service.censor(request.text, detections),
        summary=MaskSummary(
            total=len(detections),
            by_type=dict(Counter(rule_id for rule_id, _, _ in detections)),
        ),
        matches=[
            MaskMatch(rule_id=rule_id, label=label, start=d["position"][0], end=d["position"][1])
            for rule_id, label, d in detections
        ] if request.include_matches else None,
        processing_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
    )
