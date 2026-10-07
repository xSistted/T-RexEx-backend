from fastapi import APIRouter

from app.api.v1.routes import health, detect, mask, rules

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(rules.router)
api_router.include_router(detect.router)
api_router.include_router(mask.router)
