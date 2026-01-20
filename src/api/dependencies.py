"""FastAPI dependencies for dependency injection.

Provides factory functions for injecting services and repositories
into route handlers using FastAPI's Depends mechanism.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.session import async_session_maker

# =============================================================================
# Database Session
# =============================================================================


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Get database session.
    
    Yields:
        AsyncSession for database operations
    """
    async with async_session_maker() as session:
        yield session


# Type alias for dependency injection
DBSession = Annotated[AsyncSession, Depends(get_db)]


# =============================================================================
# Repository Dependencies
# =============================================================================


async def get_candlestick_repository(
    session: DBSession,
):
    """Get CandlestickRepository instance.
    
    Args:
        session: Database session (injected)
        
    Returns:
        CandlestickRepository instance
    """
    from models.repositories.candlestick import CandlestickRepository
    return CandlestickRepository(session)


async def get_ml_prediction_repository(
    session: DBSession,
):
    """Get MLPredictionRepository instance.
    
    Args:
        session: Database session (injected)
        
    Returns:
        MLPredictionRepository instance
    """
    from models.repositories.ml_predictions import MLPredictionRepository
    return MLPredictionRepository(session)


# =============================================================================
# Service Dependencies
# =============================================================================


async def get_investor_analyzer():
    """Get LazyInvestorAnalyzer instance.
    
    Returns:
        LazyInvestorAnalyzer singleton
    """
    from service.analysis.investor import get_investor_analyzer
    return get_investor_analyzer()


async def get_portfolio_manager():
    """Get PortfolioManager instance.
    
    Returns:
        PortfolioManager singleton
    """
    from service.portfolio import get_portfolio_manager
    return get_portfolio_manager()


async def get_alert_manager():
    """Get AlertManager instance.
    
    Returns:
        AlertManager singleton
    """
    from service.alerts import get_alert_manager
    return get_alert_manager()


async def get_ha_manager():
    """Get HAIntegrationManager instance.
    
    Returns:
        HAIntegrationManager singleton
    """
    from service.ha import get_ha_manager
    return get_ha_manager()


async def get_backfill_manager():
    """Get BackfillManager instance.
    
    Returns:
        BackfillManager singleton
    """
    from service.backfill import get_backfill_manager
    return get_backfill_manager()


# =============================================================================
# Type Aliases for Route Parameters
# =============================================================================


# Repository types
CandlestickRepo = Annotated[
    "CandlestickRepository",
    Depends(get_candlestick_repository),
]

MLPredictionRepo = Annotated[
    "MLPredictionRepository",
    Depends(get_ml_prediction_repository),
]

# Service types
InvestorAnalyzer = Annotated[
    "LazyInvestorAnalyzer",
    Depends(get_investor_analyzer),
]

PortfolioManager = Annotated[
    "PortfolioManager",
    Depends(get_portfolio_manager),
]

AlertManager = Annotated[
    "AlertManager",
    Depends(get_alert_manager),
]

HAManager = Annotated[
    "HAIntegrationManager",
    Depends(get_ha_manager),
]
