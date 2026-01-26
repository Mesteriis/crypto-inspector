from fastapi import APIRouter

from api.routes import (
    ai,
    alerts,
    analysis,
    backfill,
    backtest,
    briefing,
    bybit,
    candles,
    goals,
    health,
    integration,
    investor,
    portfolio,
    sensors,
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
api_router.include_router(ai.router)
api_router.include_router(backtest.router)
api_router.include_router(sensors.router)
api_router.include_router(integration.router)
