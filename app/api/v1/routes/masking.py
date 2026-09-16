"""Data-masking endpoints."""

from fastapi import APIRouter

from app.schemas.masking import MaskRequest, MaskResponse
from app.services.masking_service import mask_text


router = APIRouter(
    prefix="/mask",
    tags=["masking"],
)


@router.post(
    "",
    response_model=MaskResponse,
    summary="Mask sensitive customer data",
)
def mask_data(payload: MaskRequest) -> MaskResponse:
    return MaskResponse(
        masked_text=mask_text(payload.text)
    )