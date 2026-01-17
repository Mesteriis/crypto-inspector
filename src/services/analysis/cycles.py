"""
BTC Market Cycle Detection Module.

Analyzes Bitcoin market cycles based on:
- Halving dates
- Price distance from ATH/ATL
- Market phases (8 phases)
- Cycle position indicator
"""

import logging
from dataclasses import dataclass
from datetime import date
from enum import Enum

logger = logging.getLogger(__name__)


class CyclePhase(str, Enum):
    """Market cycle phases."""

    CAPITULATION = "capitulation"
    ACCUMULATION = "accumulation"
    EARLY_BULL = "early_bull"
    BULL_RUN = "bull_run"
    EUPHORIA = "euphoria"
    DISTRIBUTION = "distribution"
    EARLY_BEAR = "early_bear"
    BEAR_MARKET = "bear_market"
    UNKNOWN = "unknown"


# Phase descriptions and recommendations
PHASE_INFO = {
    CyclePhase.CAPITULATION: {
        "name": "Capitulation",
        "name_ru": "Capitulation",
        "description": "Maximum fear, panic selling, bottom formation",
        "description_ru": "Maximum fear, panic selling, bottom formation",
        "recommendation": "Excellent time for long-term accumulation",
        "risk_level": "low",
        "expected_duration_months": (1, 3),
    },
    CyclePhase.ACCUMULATION: {
        "name": "Accumulation",
        "name_ru": "Accumulation",
        "description": "Smart money accumulates, low volatility",
        "description_ru": "Smart money accumulates, low volatility",
        "recommendation": "Good time for DCA, building positions",
        "risk_level": "low",
        "expected_duration_months": (6, 12),
    },
    CyclePhase.EARLY_BULL: {
        "name": "Early Bull",
        "name_ru": "Early Bull",
        "description": "Trend reversal, recovery begins",
        "description_ru": "Trend reversal, recovery begins",
        "recommendation": "Continue accumulation, momentum building",
        "risk_level": "low",
        "expected_duration_months": (3, 6),
    },
    CyclePhase.BULL_RUN: {
        "name": "Bull Run",
        "name_ru": "Bull Run",
        "description": "Strong uptrend, new highs",
        "description_ru": "Strong uptrend, new highs",
        "recommendation": "Ride the trend, consider taking some profits",
        "risk_level": "medium",
        "expected_duration_months": (6, 12),
    },
    CyclePhase.EUPHORIA: {
        "name": "Euphoria",
        "name_ru": "Euphoria",
        "description": "Extreme greed, parabolic moves, FOMO",
        "description_ru": "Extreme greed, parabolic moves, FOMO",
        "recommendation": "Take profits, high risk of correction",
        "risk_level": "high",
        "expected_duration_months": (1, 3),
    },
    CyclePhase.DISTRIBUTION: {
        "name": "Distribution",
        "name_ru": "Distribution",
        "description": "Smart money selling, top formation",
        "description_ru": "Smart money selling, top formation",
        "recommendation": "Reduce exposure, protect profits",
        "risk_level": "high",
        "expected_duration_months": (1, 3),
    },
    CyclePhase.EARLY_BEAR: {
        "name": "Early Bear",
        "name_ru": "Early Bear",
        "description": "Trend reversal down, denial phase",
        "description_ru": "Trend reversal down, denial phase",
        "recommendation": "Minimize exposure, wait for stabilization",
        "risk_level": "high",
        "expected_duration_months": (3, 6),
    },
    CyclePhase.BEAR_MARKET: {
        "name": "Bear Market",
        "name_ru": "Bear Market",
        "description": "Extended downtrend, capitulation forming",
        "description_ru": "Extended downtrend, capitulation forming",
        "recommendation": "Start small DCA, prepare for accumulation",
        "risk_level": "medium",
        "expected_duration_months": (6, 12),
    },
    CyclePhase.UNKNOWN: {
        "name": "Unknown",
        "name_ru": "Unknown",
        "description": "Insufficient data to determine phase",
        "description_ru": "Insufficient data to determine phase",
        "recommendation": "Wait for clearer signals",
        "risk_level": "medium",
        "expected_duration_months": (0, 0),
    },
}

# Bitcoin halving dates
HALVING_DATES = [
    date(2012, 11, 28),
    date(2016, 7, 9),
    date(2020, 5, 11),
    date(2024, 4, 20),
    date(2028, 4, 15),  # Estimated
    date(2032, 4, 15),  # Estimated
]

# Historical ATH data (approximate)
BTC_ATH_HISTORY = [
    {"date": date(2013, 11, 30), "price": 1163},
    {"date": date(2017, 12, 17), "price": 19783},
    {"date": date(2021, 11, 10), "price": 69000},
]


@dataclass
class CycleInfo:
    """BTC market cycle information."""

    phase: CyclePhase
    phase_name: str
    phase_name_ru: str
    description: str
    recommendation: str
    risk_level: str

    # Halving info
    last_halving: date
    next_halving: date
    days_since_halving: int
    days_to_next_halving: int

    # Price context
    current_price: float
    ath_price: float
    atl_price: float
    distance_from_ath_pct: float
    distance_from_atl_pct: float

    # Cycle position (0-100)
    cycle_position: float
    confidence: float

    def to_dict(self) -> dict:
        return {
            "phase": self.phase.value,
            "phase_name": self.phase_name,
            "phase_name_ru": self.phase_name_ru,
            "description": self.description,
            "recommendation": self.recommendation,
            "risk_level": self.risk_level,
            "halving": {
                "last": self.last_halving.isoformat(),
                "next": self.next_halving.isoformat(),
                "days_since": self.days_since_halving,
                "days_to_next": self.days_to_next_halving,
            },
            "price": {
                "current": self.current_price,
                "ath": self.ath_price,
                "atl": self.atl_price,
                "from_ath_pct": self.distance_from_ath_pct,
                "from_atl_pct": self.distance_from_atl_pct,
            },
            "cycle_position": self.cycle_position,
            "confidence": self.confidence,
        }


class CycleDetector:
    """Detects BTC market cycle phases."""

    def __init__(self, ath_price: float = 69000, atl_price: float = 15500):
        """
        Initialize cycle detector.

        Args:
            ath_price: All-time high price
            atl_price: Cycle low price
        """
        self.ath_price = ath_price
        self.atl_price = atl_price

    def get_halving_info(self) -> tuple[date, date, int, int]:
        """
        Get halving dates info.

        Returns:
            Tuple (last_halving, next_halving, days_since, days_to_next)
        """
        today = date.today()

        last_halving = HALVING_DATES[0]
        next_halving = HALVING_DATES[-1]

        for i, halving in enumerate(HALVING_DATES):
            if halving <= today:
                last_halving = halving
                if i + 1 < len(HALVING_DATES):
                    next_halving = HALVING_DATES[i + 1]
            else:
                next_halving = halving
                break

        days_since = (today - last_halving).days
        days_to_next = (next_halving - today).days

        return last_halving, next_halving, days_since, days_to_next

    def detect_phase(
        self,
        current_price: float,
        rsi: float | None = None,
        days_since_halving: int | None = None,
    ) -> CyclePhase:
        """
        Detect current market phase.

        Args:
            current_price: Current BTC price
            rsi: RSI value (optional)
            days_since_halving: Days since last halving

        Returns:
            CyclePhase
        """
        # Price position relative to ATH
        from_ath_pct = ((self.ath_price - current_price) / self.ath_price) * 100
        # from_atl_pct used for future extensions
        _ = ((current_price - self.atl_price) / self.atl_price) * 100

        # Get halving info if not provided
        if days_since_halving is None:
            _, _, days_since_halving, _ = self.get_halving_info()

        # Phase detection logic based on price position and halving cycle
        # Typical cycle: ~4 years (1460 days)

        # Very close to ATH or new ATH
        if from_ath_pct < 5:
            return CyclePhase.EUPHORIA
        elif from_ath_pct < 20:
            # Check if we're going up or down
            if days_since_halving < 365 * 2:  # Within 2 years of halving
                return CyclePhase.BULL_RUN
            else:
                return CyclePhase.DISTRIBUTION

        # Very close to cycle low
        elif from_ath_pct > 80:
            if rsi and rsi < 30:
                return CyclePhase.CAPITULATION
            return CyclePhase.ACCUMULATION

        # Middle ground - use halving cycle timing
        elif days_since_halving < 180:  # 0-6 months after halving
            return CyclePhase.ACCUMULATION
        elif days_since_halving < 365:  # 6-12 months after halving
            return CyclePhase.EARLY_BULL
        elif days_since_halving < 540:  # 12-18 months after halving
            if from_ath_pct < 30:
                return CyclePhase.EUPHORIA
            return CyclePhase.BULL_RUN
        elif days_since_halving < 730:  # 18-24 months after halving
            if from_ath_pct < 50:
                return CyclePhase.DISTRIBUTION
            return CyclePhase.EARLY_BEAR
        elif days_since_halving < 1095:  # 24-36 months after halving
            if from_ath_pct > 60:
                return CyclePhase.BEAR_MARKET
            return CyclePhase.EARLY_BEAR
        else:  # 36+ months after halving
            if from_ath_pct > 70:
                return CyclePhase.CAPITULATION if rsi and rsi < 30 else CyclePhase.ACCUMULATION
            return CyclePhase.BEAR_MARKET

    def calculate_cycle_position(self, days_since_halving: int) -> float:
        """
        Calculate position in the 4-year cycle.

        Args:
            days_since_halving: Days since last halving

        Returns:
            Position 0-100 (0=halving, 100=next halving)
        """
        cycle_length = 365 * 4  # ~4 years
        position = (days_since_halving % cycle_length) / cycle_length * 100
        return round(position, 1)

    def detect_cycle(
        self,
        current_price: float,
        rsi: float | None = None,
    ) -> CycleInfo:
        """
        Full cycle detection.

        Args:
            current_price: Current BTC price
            rsi: RSI value (optional)

        Returns:
            CycleInfo with full cycle data
        """
        last_halving, next_halving, days_since, days_to_next = self.get_halving_info()

        # Detect phase
        phase = self.detect_phase(current_price, rsi, days_since)
        phase_info = PHASE_INFO[phase]

        # Calculate distances
        from_ath_pct = round(((self.ath_price - current_price) / self.ath_price) * 100, 2)
        from_atl_pct = round(((current_price - self.atl_price) / self.atl_price) * 100, 2)

        # Cycle position
        cycle_position = self.calculate_cycle_position(days_since)

        # Confidence based on data quality
        confidence = 70 if rsi else 50

        return CycleInfo(
            phase=phase,
            phase_name=phase_info["name"],
            phase_name_ru=phase_info["name_ru"],
            description=phase_info["description"],
            recommendation=phase_info["recommendation"],
            risk_level=phase_info["risk_level"],
            last_halving=last_halving,
            next_halving=next_halving,
            days_since_halving=days_since,
            days_to_next_halving=days_to_next,
            current_price=current_price,
            ath_price=self.ath_price,
            atl_price=self.atl_price,
            distance_from_ath_pct=from_ath_pct,
            distance_from_atl_pct=from_atl_pct,
            cycle_position=cycle_position,
            confidence=confidence,
        )

    def update_ath(self, new_ath: float) -> None:
        """Update ATH price."""
        if new_ath > self.ath_price:
            self.ath_price = new_ath
            logger.info(f"New ATH recorded: ${new_ath:,.0f}")

    def update_atl(self, new_atl: float) -> None:
        """Update cycle low price."""
        if new_atl < self.atl_price:
            self.atl_price = new_atl
            logger.info(f"New cycle low recorded: ${new_atl:,.0f}")
