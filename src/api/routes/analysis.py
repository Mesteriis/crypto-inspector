"""
Analysis API Routes.

Provides REST endpoints for crypto analysis:
- GET /api/analysis/{symbol} - Full analysis for a symbol
- GET /api/analysis/{symbol}/score - Composite score
- GET /api/market/summary - Market overview
- GET /api/market/fear-greed - Fear & Greed Index
- POST /api/analysis/trigger - Manual analysis trigger
"""

import logging
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.constants import PriceDefaults
from services.analysis import (
    CycleDetector,
    DerivativesAnalyzer,
    OnChainAnalyzer,
    ScoringEngine,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


def get_symbols() -> list[str]:
    """Get configured symbols from environment (deprecated - use get_currency_list instead)."""
    symbols_env = os.environ.get("HA_SYMBOLS", "BTC/USDT,ETH/USDT")
    return [s.strip().split("/")[0] for s in symbols_env.split(",") if s.strip()]


def get_currency_list() -> list[str]:
    """Get the dynamic currency list from Home Assistant input_select helper.
    
    This is the single source of truth for currency selections across the application.
    Returns coin symbols without exchange suffix (e.g., ["BTC", "ETH"]).
    
    Returns:
        List of currency symbols (e.g., ["BTC", "ETH"])
    """
    from services.ha_sensors import get_currency_list as get_dynamic_currency_list
    
    # Get full currency pairs and extract base symbols
    full_pairs = get_dynamic_currency_list()
    return [pair.split("/")[0] for pair in full_pairs if "/" in pair]


@router.get("/analysis/{symbol}")
async def get_analysis(symbol: str) -> dict[str, Any]:
    """
    Get full analysis for a symbol.

    Args:
        symbol: Coin symbol (e.g., BTC, ETH)

    Returns:
        Full analysis data including technical indicators, patterns, score
    """
    symbol = symbol.upper()

    try:
        # Initialize analyzers
        # Note: TechnicalAnalyzer, PatternDetector, ScoringEngine require candle data
        # For now, only use analyzers that don't need candles
        onchain = OnChainAnalyzer()
        derivatives = DerivativesAnalyzer()
        cycles = CycleDetector()

        # We need candle data - for now return a placeholder
        # In real implementation, fetch from database
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "status": "ok",
            "message": "Analysis requires candlestick data - use sync job first",
            "endpoints": {
                "score": f"/api/analysis/{symbol}/score",
                "fear_greed": "/api/market/fear-greed",
                "derivatives": f"/api/analysis/{symbol}/derivatives",
            },
        }

        # Fetch on-chain data (doesn't need candles)
        try:
            onchain_data = await onchain.analyze()
            result["onchain"] = onchain_data.to_dict()
        except Exception as e:
            logger.warning(f"On-chain fetch failed: {e}")
            result["onchain"] = None
        finally:
            await onchain.close()

        # Fetch derivatives data
        try:
            deriv_data = await derivatives.analyze(symbol)
            result["derivatives"] = deriv_data.to_dict()
        except Exception as e:
            logger.warning(f"Derivatives fetch failed: {e}")
            result["derivatives"] = None
        finally:
            await derivatives.close()

        # Cycle analysis for BTC
        if symbol == "BTC":
            # Get current price from derivatives
            current_price = PriceDefaults.PLACEHOLDER_BTC
            if result.get("derivatives") and result["derivatives"].get("funding"):
                current_price = result["derivatives"]["funding"].get("mark_price", PriceDefaults.PLACEHOLDER_BTC)

            cycle_info = cycles.detect_cycle(current_price)
            result["cycle"] = cycle_info.to_dict()

        return result

    except Exception as e:
        logger.error(f"Analysis error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{symbol}/score")
async def get_score(symbol: str) -> dict[str, Any]:
    """
    Get composite score for a symbol.

    Args:
        symbol: Coin symbol

    Returns:
        Composite score data
    """
    symbol = symbol.upper()

    try:
        scoring = ScoringEngine()
        onchain = OnChainAnalyzer()
        derivatives = DerivativesAnalyzer()
        cycles = CycleDetector()

        # Fetch available data
        fg_value = None
        deriv_data = None
        cycle_data = None

        try:
            onchain_data = await onchain.analyze()
            if onchain_data.fear_greed:
                fg_value = onchain_data.fear_greed.value
        except Exception:
            pass
        finally:
            await onchain.close()

        try:
            deriv_result = await derivatives.analyze(symbol)
            deriv_data = {
                "funding_rate": deriv_result.funding.rate if deriv_result.funding else None,
                "long_short_ratio": deriv_result.long_short.long_short_ratio if deriv_result.long_short else None,
            }
        except Exception:
            pass
        finally:
            await derivatives.close()

        if symbol == "BTC":
            current_price = PriceDefaults.PLACEHOLDER_BTC
            cycle_info = cycles.detect_cycle(current_price)
            cycle_data = {
                "phase": cycle_info.phase.value,
                "phase_name_ru": cycle_info.phase_name_ru,
                "days_since_halving": cycle_info.days_since_halving,
                "distance_from_ath_pct": cycle_info.distance_from_ath_pct,
            }

        # Calculate score without technical indicators (need candles)
        score = scoring.calculate(
            symbol=symbol,
            indicators=None,  # Would need candles
            pattern_summary=None,  # Would need candles
            cycle_data=cycle_data,
            fg_value=fg_value,
            deriv_data=deriv_data,
        )

        return score.to_dict()

    except Exception as e:
        logger.error(f"Score error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{symbol}/derivatives")
async def get_derivatives(symbol: str) -> dict[str, Any]:
    """
    Get derivatives data for a symbol.

    Args:
        symbol: Coin symbol

    Returns:
        Derivatives metrics
    """
    symbol = symbol.upper()

    try:
        analyzer = DerivativesAnalyzer()
        try:
            data = await analyzer.analyze(symbol)
            return data.to_dict()
        finally:
            await analyzer.close()

    except Exception as e:
        logger.error(f"Derivatives error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/summary")
async def get_market_summary() -> dict[str, Any]:
    """
    Get market summary for all configured symbols.

    Returns:
        Market summary with Fear & Greed, BTC cycle, and derivatives
    """
    try:
        symbols = get_currency_list()
        onchain = OnChainAnalyzer()
        derivatives = DerivativesAnalyzer()
        cycles = CycleDetector()

        result = {
            "timestamp": datetime.now().isoformat(),
            "symbols": symbols,
            "fear_greed": None,
            "btc_cycle": None,
            "derivatives": {},
        }

        # Fear & Greed
        try:
            onchain_data = await onchain.analyze()
            if onchain_data.fear_greed:
                result["fear_greed"] = onchain_data.fear_greed.to_dict()
            if onchain_data.network:
                result["btc_network"] = onchain_data.network.to_dict()
        except Exception as e:
            logger.warning(f"On-chain fetch failed: {e}")
        finally:
            await onchain.close()

        # BTC Cycle
        try:
            cycle_info = cycles.detect_cycle(PriceDefaults.PLACEHOLDER_BTC)
            result["btc_cycle"] = {
                "phase": cycle_info.phase.value,
                "phase_name": cycle_info.phase_name,
                "recommendation": cycle_info.recommendation,
                "risk_level": cycle_info.risk_level,
                "days_since_halving": cycle_info.days_since_halving,
                "days_to_next_halving": cycle_info.days_to_next_halving,
            }
        except Exception as e:
            logger.warning(f"Cycle analysis failed: {e}")

        # Derivatives for BTC and ETH
        try:
            for sym in ["BTC", "ETH"]:
                if sym in symbols or f"{sym}/USDT" in symbols or f"{sym}USDT" in symbols:
                    deriv_data = await derivatives.analyze(sym)
                    result["derivatives"][sym] = {
                        "funding_rate": deriv_data.funding.rate if deriv_data.funding else None,
                        "funding_rate_pct": deriv_data.funding.rate * 100 if deriv_data.funding else None,
                        "long_short_ratio": deriv_data.long_short.long_short_ratio if deriv_data.long_short else None,
                        "signal": deriv_data.signal,
                    }
        except Exception as e:
            logger.warning(f"Derivatives fetch failed: {e}")
        finally:
            await derivatives.close()

        return result

    except Exception as e:
        logger.error(f"Market summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/fear-greed")
async def get_fear_greed() -> dict[str, Any]:
    """
    Get Fear & Greed Index.

    Returns:
        Fear & Greed data with signal interpretation
    """
    try:
        analyzer = OnChainAnalyzer()
        try:
            data = await analyzer.fetch_fear_greed()
            if not data:
                raise HTTPException(status_code=503, detail="Fear & Greed API unavailable")

            signal = analyzer.get_fear_greed_signal(data.value)

            return {
                "value": data.value,
                "classification": data.classification,
                "timestamp": data.timestamp,
                "signal": signal["signal"],
                "description": signal["description"],
                "score_adjustment": signal["score_adjustment"],
            }
        finally:
            await analyzer.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fear & Greed error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analysis/trigger")
async def trigger_analysis(
    symbols: list[str] = Query(default=None, description="Symbols to analyze"),
) -> dict[str, Any]:
    """
    Trigger manual analysis run.

    Args:
        symbols: Optional list of symbols to analyze

    Returns:
        Trigger confirmation
    """
    if not symbols:
        symbols = get_currency_list()

    # In a real implementation, this would trigger the analysis job
    return {
        "status": "triggered",
        "symbols": symbols,
        "message": "Analysis job has been triggered",
        "timestamp": datetime.now().isoformat(),
    }
