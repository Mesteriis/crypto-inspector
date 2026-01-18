"""
Investor Analysis API Routes.

Provides REST endpoints for lazy investor signals:
- GET /api/investor/status - Full investor status
- GET /api/investor/dca - DCA recommendation
- GET /api/investor/red-flags - Active red flags
- POST /api/investor/configure - Configure DCA parameters
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from services.analysis import (
    DerivativesAnalyzer,
    OnChainAnalyzer,
    get_investor_analyzer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/investor", tags=["investor"])


@router.get("/status")
async def get_investor_status() -> dict[str, Any]:
    """
    Get complete investor status.

    Returns all lazy investor signals:
    - Do Nothing OK indicator
    - Market phase
    - Calm indicator
    - Red flags
    - Market tension
    - Price context
    - DCA recommendation
    - Weekly insight
    """
    try:
        analyzer = get_investor_analyzer()
        onchain = OnChainAnalyzer()
        derivatives = DerivativesAnalyzer()

        # Fetch data from various sources
        fear_greed = None
        btc_dominance = None
        funding_rate = None
        long_short_ratio = None
        btc_price = None

        try:
            onchain_data = await onchain.analyze()
            if onchain_data.fear_greed:
                fear_greed = onchain_data.fear_greed.value
            # Note: dominance not available in OnChainMetrics
        except Exception as e:
            logger.warning(f"On-chain fetch failed: {e}")
        finally:
            await onchain.close()

        try:
            deriv_data = await derivatives.analyze("BTC")
            if deriv_data.funding:
                funding_rate = deriv_data.funding.rate
                btc_price = deriv_data.funding.mark_price
            if deriv_data.long_short:
                long_short_ratio = deriv_data.long_short.long_short_ratio
        except Exception as e:
            logger.warning(f"Derivatives fetch failed: {e}")
        finally:
            await derivatives.close()

        # Calculate 6-month average price (placeholder - would need historical data)
        btc_price_avg_6m = btc_price * 0.95 if btc_price else None  # Simplified

        # Analyze
        status = await analyzer.analyze(
            fear_greed=fear_greed,
            btc_price=btc_price,
            btc_price_avg_6m=btc_price_avg_6m,
            funding_rate=funding_rate,
            long_short_ratio=long_short_ratio,
            btc_dominance=btc_dominance,
        )

        # Check if alert needed
        alert = analyzer.get_alert_if_needed(status)

        result = status.to_dict()
        if alert:
            result["alert"] = alert

        return result

    except Exception as e:
        logger.error(f"Investor status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dca")
async def get_dca_recommendation(
    weekly_budget: float = Query(default=100.0, description="Weekly DCA budget in EUR"),
    btc_weight: float = Query(default=0.5, ge=0, le=1, description="BTC allocation weight"),
    eth_weight: float = Query(default=0.3, ge=0, le=1, description="ETH allocation weight"),
    alts_weight: float = Query(default=0.2, ge=0, le=1, description="Alts allocation weight"),
) -> dict[str, Any]:
    """
    Get DCA recommendation with custom parameters.

    Returns:
        DCA signal, recommended amounts, and reasoning
    """
    try:
        analyzer = get_investor_analyzer()
        analyzer.set_dca_config(
            weekly_budget=weekly_budget,
            btc_weight=btc_weight,
            eth_weight=eth_weight,
            alts_weight=alts_weight,
        )

        onchain = OnChainAnalyzer()
        fear_greed = None

        try:
            onchain_data = await onchain.analyze()
            if onchain_data.fear_greed:
                fear_greed = onchain_data.fear_greed.value
        except Exception:
            pass
        finally:
            await onchain.close()

        status = await analyzer.analyze(fear_greed=fear_greed)

        return {
            "signal": status.dca_signal,
            "signal_ru": status.dca_signal_ru,
            "state": status.to_dict()["dca"]["state"],
            "total_amount": status.dca_total_amount,
            "btc_amount": status.dca_btc_amount,
            "eth_amount": status.dca_eth_amount,
            "alts_amount": status.dca_alts_amount,
            "reason": status.dca_reason,
            "reason_ru": status.dca_reason_ru,
            "next_dca": status.next_dca_date,
            "config": {
                "weekly_budget": weekly_budget,
                "btc_weight": btc_weight,
                "eth_weight": eth_weight,
                "alts_weight": alts_weight,
            },
        }

    except Exception as e:
        logger.error(f"DCA recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/red-flags")
async def get_red_flags() -> dict[str, Any]:
    """
    Get currently active red flags.

    Returns:
        List of active red flags with severity and descriptions
    """
    try:
        analyzer = get_investor_analyzer()
        onchain = OnChainAnalyzer()
        derivatives = DerivativesAnalyzer()

        # Fetch data
        fear_greed = None
        funding_rate = None
        long_short_ratio = None

        try:
            onchain_data = await onchain.analyze()
            if onchain_data.fear_greed:
                fear_greed = onchain_data.fear_greed.value
        except Exception:
            pass
        finally:
            await onchain.close()

        try:
            deriv_data = await derivatives.analyze("BTC")
            if deriv_data.funding:
                funding_rate = deriv_data.funding.rate
            if deriv_data.long_short:
                long_short_ratio = deriv_data.long_short.long_short_ratio
        except Exception:
            pass
        finally:
            await derivatives.close()

        status = await analyzer.analyze(
            fear_greed=fear_greed,
            funding_rate=funding_rate,
            long_short_ratio=long_short_ratio,
        )

        red_flags_data = status.to_dict()["red_flags"]

        return {
            "count": red_flags_data["count"],
            "flags": red_flags_data["flags"],
            "flags_list_ru": red_flags_data["flags_list"],
            "severity_summary": {
                "critical": len([f for f in status.red_flags if f.severity == "critical"]),
                "danger": len([f for f in status.red_flags if f.severity == "danger"]),
                "warning": len([f for f in status.red_flags if f.severity == "warning"]),
            },
            "alert_needed": len([f for f in status.red_flags if f.severity in ["critical", "danger"]]) > 0,
        }

    except Exception as e:
        logger.error(f"Red flags error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phase")
async def get_market_phase() -> dict[str, Any]:
    """
    Get current market phase analysis.

    Returns:
        Market phase with confidence and description
    """
    try:
        analyzer = get_investor_analyzer()
        onchain = OnChainAnalyzer()

        fear_greed = None
        btc_dominance = None

        try:
            onchain_data = await onchain.analyze()
            if onchain_data.fear_greed:
                fear_greed = onchain_data.fear_greed.value
            # Note: dominance not available in OnChainMetrics
        except Exception:
            pass
        finally:
            await onchain.close()

        status = await analyzer.analyze(
            fear_greed=fear_greed,
            btc_dominance=btc_dominance,
        )

        phase_data = status.to_dict()["phase"]

        return {
            "phase": phase_data["value"],
            "phase_name": phase_data["name"],
            "phase_name_ru": phase_data["name_ru"],
            "confidence": phase_data["confidence"],
            "description": phase_data["description"],
            "description_ru": phase_data["description_ru"],
            "risk_level": status.risk_level.value,
            "risk_level_ru": status.to_dict()["risk_level"]["name_ru"],
        }

    except Exception as e:
        logger.error(f"Market phase error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configure")
async def configure_investor(
    weekly_budget: float = Query(default=100.0, description="Weekly DCA budget"),
    btc_weight: float = Query(default=0.5, description="BTC weight"),
    eth_weight: float = Query(default=0.3, description="ETH weight"),
    alts_weight: float = Query(default=0.2, description="Alts weight"),
) -> dict[str, Any]:
    """
    Configure investor analyzer parameters.

    These settings persist until the application restarts.
    """
    analyzer = get_investor_analyzer()
    analyzer.set_dca_config(
        weekly_budget=weekly_budget,
        btc_weight=btc_weight,
        eth_weight=eth_weight,
        alts_weight=alts_weight,
    )

    return {
        "status": "configured",
        "config": {
            "weekly_budget": weekly_budget,
            "btc_weight": btc_weight,
            "eth_weight": eth_weight,
            "alts_weight": alts_weight,
        },
    }


@router.get("/ml-insights")
async def get_ml_investment_insights(
    symbols: list[str] = Query(default=["BTC/USDT", "ETH/USDT"], description="Symbols to analyze"),
    risk_tolerance: str = Query(default="moderate", enum=["conservative", "moderate", "aggressive"]),
    timeframe: str = Query(default="medium_term", enum=["short_term", "medium_term", "long_term"]),
) -> dict[str, Any]:
    """
    Get ML-powered investment insights for lazy investors.

    Transforms raw ML predictions into market awareness signals:
    - Market condition assessment
    - Risk level evaluation
    - Portfolio positioning advice
    - Opportunity identification

    This endpoint focuses on informed decision-making rather than active trading.
    """
    try:
        # Import here to avoid circular imports
        from services.investor.lazy_investor_ml import LazyInvestorMLAdvisor

        advisor = LazyInvestorMLAdvisor()

        # Get investment signals
        signals = await advisor.generate_investment_signals(symbols)
        portfolio_health = await advisor.get_portfolio_health_score(symbols)
        daily_briefing = await advisor.generate_daily_briefing(symbols)

        # Filter signals by confidence level based on risk tolerance
        confidence_thresholds = {
            "conservative": 0.8,  # Only high-confidence signals
            "moderate": 0.7,  # Medium+ confidence
            "aggressive": 0.6,  # All signals above noise floor
        }

        threshold = confidence_thresholds[risk_tolerance]
        filtered_signals = [
            s
            for s in signals
            if (
                (s.confidence_level == "high" and threshold <= 0.8)
                or (s.confidence_level == "medium" and threshold <= 0.7)
                or (s.confidence_level == "low" and threshold <= 0.6)
            )
        ]

        # Generate personalized strategy recommendation
        strategy_mapping = {
            "conservative": {
                "focus": "Capital preservation",
                "action_bias": "Minimal intervention - only act on strong risk signals",
                "review_frequency": "Monthly portfolio review",
                "volatility_response": "Increase DCA frequency during high volatility",
            },
            "moderate": {
                "focus": "Balanced growth with risk awareness",
                "action_bias": "Monitor medium+ confidence signals, act on strong consensus",
                "review_frequency": "Quarterly portfolio review",
                "volatility_response": "Adjust DCA amounts based on market conditions",
            },
            "aggressive": {
                "focus": "Opportunistic growth with risk management",
                "action_bias": "Act on medium+ confidence opportunities, hedge against risks",
                "review_frequency": "Monthly tactical review",
                "volatility_response": "Use volatility for strategic positioning",
            },
        }

        strategy = strategy_mapping[risk_tolerance]

        return {
            "timestamp": datetime.now().isoformat(),
            "request_params": {"symbols": symbols, "risk_tolerance": risk_tolerance, "timeframe": timeframe},
            "portfolio_health": portfolio_health,
            "strategy_recommendation": strategy,
            "market_insights": {
                "active_signals": len(filtered_signals),
                "total_signals": len(signals),
                "signal_types": {
                    "opportunities": len([s for s in filtered_signals if s.signal_type == "opportunity"]),
                    "risk_warnings": len([s for s in filtered_signals if s.signal_type == "risk_warning"]),
                    "market_shifts": len([s for s in filtered_signals if s.signal_type == "market_shift"]),
                    "hold_indicators": len([s for s in filtered_signals if s.signal_type == "hold"]),
                },
                "confidence_distribution": {
                    "high": len([s for s in signals if s.confidence_level == "high"]),
                    "medium": len([s for s in signals if s.confidence_level == "medium"]),
                    "low": len([s for s in signals if s.confidence_level == "low"]),
                },
            },
            "filtered_signals": [
                {
                    "symbol": s.symbol,
                    "signal_type": s.signal_type,
                    "confidence_level": s.confidence_level,
                    "rationale": s.rationale,
                    "suggested_action": s.suggested_action,
                    "timeframe": s.timeframe,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in filtered_signals
            ],
            "daily_briefing": daily_briefing,
            "ml_context": {
                "model_performance_note": "ML models show ~50% accuracy typical for crypto markets",
                "approach": "Using ML for market awareness, not timing",
                "philosophy": "Informed holding rather than active trading",
                "confidence_interpretation": "High confidence (>70%) signals worth reviewing, lower confidence = maintain course",
            },
        }

    except Exception as e:
        logger.error(f"ML investment insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lazy-daily-briefing")
async def get_lazy_daily_briefing(
    symbols: list[str] = Query(default=["BTC/USDT", "ETH/USDT", "SOL/USDT"], description="Portfolio symbols"),
) -> dict[str, Any]:
    """
    Get daily investment briefing tailored for passive investors.

    Provides human-readable market insights without requiring active trading decisions.
    Focuses on market context, risk awareness, and informed positioning.
    """
    try:
        from services.investor.lazy_investor_ml import LazyInvestorMLAdvisor

        advisor = LazyInvestorMLAdvisor()
        briefing = await advisor.generate_daily_briefing(symbols)
        health = await advisor.get_portfolio_health_score(symbols)
        signals = await advisor.generate_investment_signals(symbols)

        return {
            "timestamp": datetime.now().isoformat(),
            "briefing": briefing,
            "portfolio_health": health,
            "key_signals": [
                {
                    "symbol": s.symbol,
                    "type": s.signal_type,
                    "confidence": s.confidence_level,
                    "action": s.suggested_action,
                }
                for s in signals[:5]  # Top 5 most relevant signals
            ],
            "interpretation_guide": {
                "opportunity_signals": "Market conditions favorable for gradual accumulation",
                "risk_warning_signals": "Consider reviewing portfolio positioning",
                "market_shift_signals": "Normal volatility - maintain disciplined approach",
                "hold_signals": "No significant changes needed - continue current strategy",
            },
        }

    except Exception as e:
        logger.error(f"Lazy daily briefing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
