"""Aggregates every v1 route module into a single router.

Add new feature routers here — main.py only ever includes this one router.
"""

from fastapi import APIRouter

from app.api.v1.routes import health, items

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(items.router)
