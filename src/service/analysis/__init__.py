"""Crypto Analysis Services.

This package provides comprehensive cryptocurrency analysis:
- Technical Analysis (indicators, signals)
- Pattern Detection (chart patterns)
- Cycle Analysis (BTC halving cycles)
- Scoring Engine (composite recommendations)
- On-Chain Metrics (Fear & Greed, etc.)
- Derivatives Analysis (funding, OI)
- Lazy Investor Analysis (signals for passive investors)
"""

from service.analysis.cycles import CycleDetector, CycleInfo, CyclePhase
from service.analysis.derivatives import DerivativesAnalyzer, DerivativesMetrics
from service.analysis.investor import (
    InvestorStatus,
    LazyInvestorAnalyzer,
    MarketPhase,
    RedFlag,
    RiskLevel,
    get_investor_analyzer,
)
from service.analysis.onchain import OnChainAnalyzer, OnChainMetrics
from service.analysis.patterns import DetectedPattern, PatternDetector
from service.analysis.scoring import CompositeScore, ScoringEngine
from service.analysis.technical import TechnicalAnalyzer, TechnicalIndicators

__all__ = [
    # Technical
    "TechnicalAnalyzer",
    "TechnicalIndicators",
    # Patterns
    "PatternDetector",
    "DetectedPattern",
    # Scoring
    "ScoringEngine",
    "CompositeScore",
    # Cycles
    "CycleDetector",
    "CycleInfo",
    "CyclePhase",
    # On-Chain
    "OnChainAnalyzer",
    "OnChainMetrics",
    # Derivatives
    "DerivativesAnalyzer",
    "DerivativesMetrics",
    # Investor
    "LazyInvestorAnalyzer",
    "InvestorStatus",
    "MarketPhase",
    "RiskLevel",
    "RedFlag",
    "get_investor_analyzer",
]
