"""
Investor Analysis API Routes.

Provides REST endpoints for lazy investor signals:
- GET /api/investor/status - Full investor status
- GET /api/investor/dca - DCA recommendation
- GET /api/investor/red-flags - Active red flags
- POST /api/investor/configure - Configure DCA parameters
"""

import logging
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
