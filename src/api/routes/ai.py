"""
AI Analysis API Routes.

Endpoints for AI-powered market analysis:
- GET /api/ai/summary - Get latest AI summary
- POST /api/ai/analyze - Trigger new analysis
- GET /api/ai/history - Analysis history
- GET /api/ai/status - AI service status
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from schemas.api.ai import AIStatusResponse, AnalysisResponse, AnalyzeRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Analysis"])

# Global AI service instance (set from main.py)
_ai_analyzer = None
_ai_service = None


def set_ai_services(ai_service, ai_analyzer):
    """Set AI service instances from main app."""
    global _ai_service, _ai_analyzer
    _ai_service = ai_service
    _ai_analyzer = ai_analyzer


@router.get("/status")
async def get_ai_status() -> AIStatusResponse:
    """Get AI service status."""
    if not _ai_service:
        return AIStatusResponse(enabled=False, available=False)

    available_provider = await _ai_service.get_available_provider()

    last_analysis = None
    analysis_count = 0

    if _ai_analyzer:
        if _ai_analyzer.last_analysis and _ai_analyzer.last_analysis.timestamp:
            last_analysis = _ai_analyzer.last_analysis.timestamp.isoformat()
        analysis_count = len(_ai_analyzer.analysis_history)

    return AIStatusResponse(
        enabled=_ai_service.is_configured,
        available=available_provider is not None,
        provider=available_provider.name if available_provider else None,
        model=getattr(available_provider, "model", None) if available_provider else None,
        last_analysis=last_analysis,
        analysis_count=analysis_count,
    )


@router.get("/summary")
async def get_ai_summary() -> dict[str, Any]:
    """Get latest AI summary."""
    if not _ai_analyzer:
        raise HTTPException(status_code=503, detail="AI service not configured")

    if not _ai_analyzer.last_analysis:
        return {
            "available": False,
            "message": "No analysis available yet",
        }

    analysis = _ai_analyzer.last_analysis
    return {
        "available": True,
        "type": analysis.analysis_type,
        "content": analysis.content,
        "sentiment": analysis.sentiment,
        "recommendation": analysis.recommendation,
        "provider": analysis.provider,
        "model": analysis.model,
        "timestamp": analysis.timestamp.isoformat() if analysis.timestamp else None,
        "language": analysis.language,
    }


@router.get("/history")
async def get_ai_history(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Get AI analysis history."""
    if not _ai_analyzer:
        raise HTTPException(status_code=503, detail="AI service not configured")

    history = _ai_analyzer.analysis_history[-limit:]

    return {
        "count": len(history),
        "analyses": [
            {
                "type": a.analysis_type,
                "content": a.content[:200] + "..." if len(a.content) > 200 else a.content,
                "sentiment": a.sentiment,
                "recommendation": a.recommendation,
                "provider": a.provider,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            }
            for a in reversed(history)
        ],
    }


@router.post("/analyze")
async def trigger_analysis(request: AnalyzeRequest) -> AnalysisResponse:
    """
    Trigger AI analysis.

    Analysis types:
    - daily_summary: Daily market overview
    - weekly_report: Weekly comprehensive report
    - opportunity: Trading opportunity for specific symbol
    - dca: DCA recommendation
    - risk: Risk assessment
    - sentiment: Market sentiment
    """
    if not _ai_analyzer or not _ai_service:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Check if AI is available
    available = await _ai_service.get_available_provider()
    if not available:
        raise HTTPException(
            status_code=503,
            detail="No AI provider available. Check Ollama/OpenAI configuration.",
        )

    # Collect market data (simplified - in production, get from actual services)
    from service.ai.prompts import MarketData

    # Create mock market data for demo - in production, collect from services
    market_data = MarketData(
        btc_price=100000.0,
        eth_price=3500.0,
        btc_change_24h=2.5,
        eth_change_24h=1.8,
        fear_greed=65,
        fear_greed_label="Greed",
        btc_dominance=54.0,
        altseason_index=45,
    )

    result = None

    try:
        if request.analysis_type == "daily_summary":
            result = await _ai_analyzer.generate_daily_summary(market_data, language=request.language)
        elif request.analysis_type == "weekly_report":
            result = await _ai_analyzer.generate_weekly_report(market_data, language=request.language)
        elif request.analysis_type == "opportunity":
            symbol = request.symbol or "BTC"
            result = await _ai_analyzer.analyze_opportunity(symbol, market_data, language=request.language)
        elif request.analysis_type == "dca":
            result = await _ai_analyzer.get_dca_recommendation(
                market_data, base_amount=100.0, language=request.language
            )
        elif request.analysis_type == "risk":
            result = await _ai_analyzer.assess_risk(market_data, language=request.language)
        elif request.analysis_type == "sentiment":
            result = await _ai_analyzer.get_sentiment(market_data, language=request.language)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown analysis type: {request.analysis_type}",
            )

    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    if not result:
        raise HTTPException(status_code=503, detail="AI analysis returned empty result")

    return AnalysisResponse(
        type=result.analysis_type,
        content=result.content,
        sentiment=result.sentiment,
        recommendation=result.recommendation,
        provider=result.provider,
        model=result.model,
        timestamp=result.timestamp.isoformat() if result.timestamp else None,
        language=result.language,
    )


@router.get("/sensors")
async def get_ai_sensors() -> dict[str, Any]:
    """Get AI data formatted for HA sensors."""
    if not _ai_analyzer:
        return {
            "ai_daily_summary": "AI not configured",
            "ai_market_sentiment": "Unknown",
            "ai_recommendation": "N/A",
            "ai_last_analysis": "Never",
            "ai_provider": "None",
        }

    provider = None
    if _ai_service:
        p = await _ai_service.get_available_provider()
        provider = f"{p.name}/{getattr(p, 'model', 'unknown')}" if p else "None"

    return {
        "ai_daily_summary": _ai_analyzer.get_summary_for_sensor(),
        "ai_market_sentiment": _ai_analyzer.get_sentiment_for_sensor(),
        "ai_recommendation": _ai_analyzer.get_recommendation_for_sensor(),
        "ai_last_analysis": _ai_analyzer.get_last_analysis_time(),
        "ai_provider": provider or "None",
    }
