"""Crypto Analysis Services.

This package provides comprehensive cryptocurrency analysis:
- Technical Analysis (indicators, signals)
- Pattern Detection (chart patterns)
- Cycle Analysis (BTC halving cycles)
- Scoring Engine (composite recommendations)
- On-Chain Metrics (Fear & Greed, etc.)
- Derivatives Analysis (funding, OI)
"""

from services.analysis.cycles import CycleDetector, CycleInfo, CyclePhase
from services.analysis.derivatives import DerivativesAnalyzer, DerivativesMetrics
from services.analysis.onchain import OnChainAnalyzer, OnChainMetrics
from services.analysis.patterns import DetectedPattern, PatternDetector
from services.analysis.scoring import CompositeScore, ScoringEngine
from services.analysis.technical import TechnicalAnalyzer, TechnicalIndicators

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
]
