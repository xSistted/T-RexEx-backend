"""detection endpoint"""

import time
from fastapi import APIRouter

from app.core.config import settings
from app.schemas.detect import DetectRequest, DetectResponse, DetectSummary, DetectMatch

from app.services import (
    email,
    credit,
    tel_censor_service,
    dob_censor_service,
    address_censor_service,
)

router = APIRouter(tags=["detect"])

RULE_MODULES = {
    "email": (email, "อีเมล"),
    "credit_card": (credit, "เลขบัตรเครดิต"),
    "phone": (tel_censor_service, "เบอร์โทรศัพท์"),
    "dob": (dob_censor_service, "วันเกิด"),
    "address": (address_censor_service, "ที่อยู่"),
}


@router.post("/detect", summary="detect data", response_model=DetectResponse)
def detect(request: DetectRequest) -> DetectResponse:
    start_time = time.perf_counter()
    
    rules_to_run = request.enabled_rules
    if not rules_to_run:
        rules_to_run = list(RULE_MODULES.keys())
        
    total_matches = 0
    by_type = {}
    matches = [] if request.include_matches else None
    
    for rule_id in rules_to_run:
        if rule_id not in RULE_MODULES:
            continue
            
        module, label = RULE_MODULES[rule_id]
        detections = module.detect(request.text)
        
        count = len(detections)
        if count > 0:
            by_type[rule_id] = count
            total_matches += count
            
            if request.include_matches and matches is not None:
                for d in detections:
                    start, end = d["position"]
                    matches.append(
                        DetectMatch(
                            rule_id=rule_id,
                            label=label,
                            start=start,
                            end=end,
                            masked_value=None  # Can be implemented if needed
                        )
                    )
    
    # Sort matches by start position if we have any
    if matches:
        matches.sort(key=lambda x: x.start)
    
    summary = DetectSummary(
        total=total_matches,
        by_type=by_type
    )
        
    processing_time_ms = (time.perf_counter() - start_time) * 1000
    
    return DetectResponse(
        summary=summary,
        matches=matches,
        processing_time_ms=round(processing_time_ms, 2)
    )
