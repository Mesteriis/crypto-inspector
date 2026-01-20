"""
Real unit tests for CycleDetector.

Tests cover:
- Halving date detection
- Phase detection based on price and time
- Cycle position calculation
- ATH/ATL tracking
- Full cycle detection
"""

from datetime import date
from unittest.mock import patch

import pytest

from core.constants import HALVING_DATES, PriceDefaults
from service.analysis.cycles import (
    PHASE_INFO,
    CycleDetector,
    CycleInfo,
    CyclePhase,
)


class TestHalvingInfo:
    """Tests for halving date detection."""

    @pytest.fixture
    def detector(self):
        return CycleDetector()

    def test_get_halving_info_returns_tuple(self, detector):
        """Should return tuple of 4 elements."""
        result = detector.get_halving_info()

        assert isinstance(result, tuple)
        assert len(result) == 4

    def test_get_halving_info_types(self, detector):
        """Should return correct types."""
        last_halving, next_halving, days_since, days_to_next = detector.get_halving_info()

        assert isinstance(last_halving, date)
        assert isinstance(next_halving, date)
        assert isinstance(days_since, int)
        assert isinstance(days_to_next, int)

    def test_get_halving_info_dates_order(self, detector):
        """Last halving should be before next halving."""
        last_halving, next_halving, _, _ = detector.get_halving_info()

        assert last_halving < next_halving

    def test_get_halving_info_days_positive(self, detector):
        """Days should be non-negative."""
        _, _, days_since, days_to_next = detector.get_halving_info()

        assert days_since >= 0
        assert days_to_next >= 0

    @patch("service.analysis.cycles.date")
    def test_get_halving_info_with_mocked_date(self, mock_date, detector):
        """Should correctly identify halving dates for specific dates."""
        # Test date after 2024 halving but before 2028
        mock_date.today.return_value = date(2025, 1, 1)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        last_halving, next_halving, _, _ = detector.get_halving_info()

        assert last_halving == date(2024, 4, 20)
        assert next_halving == date(2028, 4, 15)


class TestPhaseDetection:
    """Tests for market phase detection."""

    @pytest.fixture
    def detector(self):
        return CycleDetector(ath_price=109000, atl_price=15500)

    def test_detect_euphoria_near_ath(self, detector):
        """Should detect euphoria when price is very close to ATH."""
        # Price 3% from ATH
        price = 109000 * 0.97
        phase = detector.detect_phase(price, days_since_halving=500)

        assert phase == CyclePhase.EUPHORIA

    def test_detect_bull_run_within_20_pct_of_ath(self, detector):
        """Should detect bull run when price is within 20% of ATH and early in cycle."""
        # Price 15% from ATH, within 2 years of halving
        price = 109000 * 0.85
        phase = detector.detect_phase(price, days_since_halving=400)

        assert phase == CyclePhase.BULL_RUN

    def test_detect_distribution_late_cycle(self, detector):
        """Should detect distribution when price near ATH but late in cycle."""
        # Price 15% from ATH, but more than 2 years after halving
        price = 109000 * 0.85
        phase = detector.detect_phase(price, days_since_halving=800)

        assert phase == CyclePhase.DISTRIBUTION

    def test_detect_accumulation_far_from_ath(self, detector):
        """Should detect accumulation when price is far from ATH."""
        # Price 85% from ATH
        price = 109000 * 0.15
        phase = detector.detect_phase(price, days_since_halving=100)

        assert phase == CyclePhase.ACCUMULATION

    def test_detect_capitulation_with_low_rsi(self, detector):
        """Should detect capitulation when price far from ATH and RSI is low."""
        price = 109000 * 0.15
        phase = detector.detect_phase(price, rsi=25, days_since_halving=900)

        assert phase == CyclePhase.CAPITULATION

    def test_detect_early_bull_after_halving(self, detector):
        """Should detect early bull 6-12 months after halving."""
        price = 109000 * 0.6  # 40% from ATH
        phase = detector.detect_phase(price, days_since_halving=250)  # ~8 months

        assert phase == CyclePhase.EARLY_BULL

    def test_detect_bear_market_late_cycle(self, detector):
        """Should detect bear market in late cycle with significant drop."""
        price = 109000 * 0.35  # 65% from ATH
        phase = detector.detect_phase(price, days_since_halving=900)  # ~2.5 years

        assert phase == CyclePhase.BEAR_MARKET

    def test_detect_early_bear(self, detector):
        """Should detect early bear 18-24 months after halving with drop."""
        price = 109000 * 0.45  # 55% from ATH
        phase = detector.detect_phase(price, days_since_halving=700)

        assert phase == CyclePhase.EARLY_BEAR


class TestCyclePosition:
    """Tests for cycle position calculation."""

    @pytest.fixture
    def detector(self):
        return CycleDetector()

    def test_calculate_cycle_position_at_halving(self, detector):
        """Position should be 0 right after halving."""
        result = detector.calculate_cycle_position(0)
        assert result == 0

    def test_calculate_cycle_position_mid_cycle(self, detector):
        """Position should be ~50 at mid cycle (~2 years)."""
        result = detector.calculate_cycle_position(730)  # 2 years
        assert 45 < result < 55

    def test_calculate_cycle_position_end_cycle(self, detector):
        """Position should be close to 100 near end of cycle."""
        result = detector.calculate_cycle_position(1400)  # Almost 4 years
        assert result > 90

    def test_calculate_cycle_position_wraps_around(self, detector):
        """Position should wrap around after 4 years."""
        result = detector.calculate_cycle_position(1500)  # Just past 4 years
        # Should wrap around to early in cycle
        assert result < 10


class TestFullCycleDetection:
    """Tests for full cycle detection."""

    @pytest.fixture
    def detector(self):
        return CycleDetector(ath_price=109000, atl_price=15500)

    def test_detect_cycle_returns_cycle_info(self, detector):
        """Should return CycleInfo object."""
        result = detector.detect_cycle(current_price=50000)

        assert isinstance(result, CycleInfo)

    def test_detect_cycle_has_all_fields(self, detector):
        """Should populate all CycleInfo fields."""
        result = detector.detect_cycle(current_price=50000)

        assert result.phase is not None
        assert result.phase_name is not None
        assert result.phase_name_ru is not None
        assert result.description is not None
        assert result.recommendation is not None
        assert result.risk_level is not None
        assert result.last_halving is not None
        assert result.next_halving is not None
        assert result.days_since_halving >= 0
        assert result.days_to_next_halving >= 0
        assert result.current_price == 50000
        assert result.ath_price == 109000
        assert result.atl_price == 15500
        assert result.distance_from_ath_pct is not None
        assert result.distance_from_atl_pct is not None
        assert result.cycle_position is not None
        assert result.confidence is not None

    def test_detect_cycle_distance_from_ath(self, detector):
        """Should correctly calculate distance from ATH."""
        result = detector.detect_cycle(current_price=54500)  # 50% from ATH

        assert 49 < result.distance_from_ath_pct < 51

    def test_detect_cycle_distance_from_atl(self, detector):
        """Should correctly calculate distance from ATL."""
        result = detector.detect_cycle(current_price=31000)  # 100% above ATL

        assert 95 < result.distance_from_atl_pct < 105

    def test_detect_cycle_with_rsi(self, detector):
        """Should use RSI for more accurate detection."""
        result_without_rsi = detector.detect_cycle(current_price=20000)
        result_with_rsi = detector.detect_cycle(current_price=20000, rsi=25)

        # With low RSI, might detect capitulation instead of accumulation
        assert result_with_rsi.confidence > result_without_rsi.confidence

    def test_detect_cycle_confidence_levels(self, detector):
        """Should have higher confidence with RSI."""
        result_without_rsi = detector.detect_cycle(current_price=50000)
        result_with_rsi = detector.detect_cycle(current_price=50000, rsi=50)

        assert result_without_rsi.confidence == 50
        assert result_with_rsi.confidence == 70


class TestATHATLUpdates:
    """Tests for ATH/ATL updates."""

    @pytest.fixture
    def detector(self):
        return CycleDetector(ath_price=100000, atl_price=15000)

    def test_update_ath_higher(self, detector):
        """Should update ATH when new price is higher."""
        detector.update_ath(110000)

        assert detector.ath_price == 110000

    def test_update_ath_lower(self, detector):
        """Should not update ATH when new price is lower."""
        detector.update_ath(90000)

        assert detector.ath_price == 100000

    def test_update_atl_lower(self, detector):
        """Should update ATL when new price is lower."""
        detector.update_atl(12000)

        assert detector.atl_price == 12000

    def test_update_atl_higher(self, detector):
        """Should not update ATL when new price is higher."""
        detector.update_atl(20000)

        assert detector.atl_price == 15000


class TestCycleInfoSerialization:
    """Tests for CycleInfo serialization."""

    @pytest.fixture
    def detector(self):
        return CycleDetector(ath_price=109000, atl_price=15500)

    def test_to_dict(self, detector):
        """to_dict() should return valid dictionary."""
        cycle_info = detector.detect_cycle(current_price=50000)

        result = cycle_info.to_dict()

        assert isinstance(result, dict)
        assert "phase" in result
        assert "phase_name" in result
        assert "halving" in result
        assert "price" in result
        assert "cycle_position" in result
        assert "confidence" in result

    def test_to_dict_halving_info(self, detector):
        """Halving info should be properly structured."""
        cycle_info = detector.detect_cycle(current_price=50000)

        result = cycle_info.to_dict()

        halving = result["halving"]
        assert "last" in halving
        assert "next" in halving
        assert "days_since" in halving
        assert "days_to_next" in halving

    def test_to_dict_price_info(self, detector):
        """Price info should be properly structured."""
        cycle_info = detector.detect_cycle(current_price=50000)

        result = cycle_info.to_dict()

        price = result["price"]
        assert "current" in price
        assert "ath" in price
        assert "atl" in price
        assert "from_ath_pct" in price
        assert "from_atl_pct" in price


class TestPhaseInfo:
    """Tests for PHASE_INFO dictionary."""

    def test_all_phases_have_info(self):
        """All CyclePhase values should have corresponding info."""
        for phase in CyclePhase:
            assert phase in PHASE_INFO

    def test_phase_info_structure(self):
        """Each phase info should have required fields."""
        required_fields = [
            "name",
            "name_ru",
            "description",
            "description_ru",
            "recommendation",
            "risk_level",
            "expected_duration_months",
        ]

        for phase, info in PHASE_INFO.items():
            for field in required_fields:
                assert field in info, f"{phase} missing {field}"

    def test_risk_levels_valid(self):
        """Risk levels should be valid values."""
        valid_levels = {"low", "medium", "high"}

        for phase, info in PHASE_INFO.items():
            assert info["risk_level"] in valid_levels


class TestDefaultValues:
    """Tests for default values from constants."""

    def test_default_ath_price(self):
        """Should use default ATH from constants."""
        detector = CycleDetector()

        assert detector.ath_price == PriceDefaults.BTC_ATH

    def test_default_atl_price(self):
        """Should use default ATL from constants."""
        detector = CycleDetector()

        assert detector.atl_price == PriceDefaults.BTC_CYCLE_LOW

    def test_halving_dates_from_constants(self):
        """Should use halving dates from constants."""
        # Just verify the constants are accessible
        assert len(HALVING_DATES) >= 4
        assert HALVING_DATES[0] == date(2012, 11, 28)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_price_at_exact_ath(self):
        """Should handle price exactly at ATH."""
        detector = CycleDetector(ath_price=100000, atl_price=15000)
        result = detector.detect_cycle(current_price=100000)

        assert result.distance_from_ath_pct == 0
        assert result.phase == CyclePhase.EUPHORIA

    def test_price_at_exact_atl(self):
        """Should handle price exactly at ATL."""
        detector = CycleDetector(ath_price=100000, atl_price=15000)
        result = detector.detect_cycle(current_price=15000)

        assert result.distance_from_atl_pct == 0

    def test_price_below_atl(self):
        """Should handle price below recorded ATL."""
        detector = CycleDetector(ath_price=100000, atl_price=15000)
        result = detector.detect_cycle(current_price=10000)

        assert result.distance_from_atl_pct < 0

    def test_price_above_ath(self):
        """Should handle new ATH price."""
        detector = CycleDetector(ath_price=100000, atl_price=15000)
        result = detector.detect_cycle(current_price=120000)

        assert result.distance_from_ath_pct < 0  # Above ATH
        assert result.phase == CyclePhase.EUPHORIA

    def test_very_low_price(self):
        """Should handle very low prices."""
        detector = CycleDetector(ath_price=100000, atl_price=15000)
        result = detector.detect_cycle(current_price=100)

        assert result is not None
        assert result.distance_from_ath_pct > 99

    def test_zero_price(self):
        """Should handle zero price gracefully."""
        detector = CycleDetector(ath_price=100000, atl_price=15000)
        result = detector.detect_cycle(current_price=0)

        assert result is not None
        assert result.distance_from_ath_pct == 100
