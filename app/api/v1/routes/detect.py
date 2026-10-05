"""Detection endpoint."""

import time
from collections import Counter
from fastapi import APIRouter

from app.schemas.detect import DetectRequest, DetectResponse, DetectSummary, DetectMatch
from app.services import masking_service

router = APIRouter(tags=["detect"])


@router.post("/detect", summary="detect data", response_model=DetectResponse)
def detect(request: DetectRequest) -> DetectResponse:
    start_time = time.perf_counter()
    detections = masking_service.detect(request.text, request.enabled_rules)
    return DetectResponse(
        summary=DetectSummary(
            total=len(detections),
            by_type=dict(Counter(rule_id for rule_id, _, _ in detections)),
        ),
        matches=[
            DetectMatch(rule_id=rule_id, label=label, start=d["position"][0], end=d["position"][1])
            for rule_id, label, d in detections
        ] if request.include_matches else None,
        processing_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
    )
