from fastapi import APIRouter

from api.routes import analysis, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(analysis.router)
