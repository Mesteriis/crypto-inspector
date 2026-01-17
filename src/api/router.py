from fastapi import APIRouter

from api.routes import analysis, health, streaming

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(analysis.router)
api_router.include_router(streaming.router)
