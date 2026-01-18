from fastapi import APIRouter

from api.routes import (
    alerts,
    analysis,
    backfill,
    briefing,
    bybit,
    candles,
    goals,
    health,
    investor,
    portfolio,
    signals,
    streaming,
    summary,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(analysis.router)
api_router.include_router(streaming.router)
api_router.include_router(candles.router)
api_router.include_router(investor.router)
api_router.include_router(portfolio.router)
api_router.include_router(alerts.router)
api_router.include_router(signals.router)
api_router.include_router(bybit.router)
api_router.include_router(backfill.router)
api_router.include_router(summary.router)
api_router.include_router(briefing.router)
api_router.include_router(goals.router)
