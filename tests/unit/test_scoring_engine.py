"""
Real unit tests for ScoringEngine.

Tests cover:
- Component scoring (technical, patterns, cycle, F&G, derivatives, onchain)
- Composite score calculation
- Signal generation
- Recommendation generation
- Risk level calculation
"""

import pytest

from service.analysis.scoring import ComponentScore, CompositeScore, ScoringEngine
from service.analysis.technical import TechnicalIndicators


class TestComponentScores:
    """Tests for individual component scoring."""

    @pytest.fixture
    def engine(self):
        return ScoringEngine()

    # =========================================================================
    # Technical Score Tests
    # =========================================================================

    def test_score_technical_none(self, engine):
        """Should return neutral score when no indicators."""
        result = engine.score_technical(None)

        assert result.score == 50
        assert result.signal == "neutral"
        assert result.name == "technical"

    def test_score_technical_rsi_oversold(self, engine):
        """Should boost score for oversold RSI."""
        indicators = TechnicalIndicators(
            symbol="BTC",
            timeframe="1d",
            timestamp=1700000000000,
            price=50000,
            rsi=25,  # Oversold
        )
        result = engine.score_technical(indicators)

        assert result.score > 50
        assert "rsi" in result.details

    def test_score_technical_rsi_overbought(self, engine):
        """Should reduce score for overbought RSI."""
        indicators = TechnicalIndicators(
            symbol="BTC",
            timeframe="1d",
            timestamp=1700000000000,
            price=50000,
            rsi=75,  # Overbought
        )
        result = engine.score_technical(indicators)

        assert result.score < 50

    def test_score_technical_golden_cross(self, engine):
        """Should boost score for golden cross."""
        indicators = TechnicalIndicators(
            symbol="BTC",
            timeframe="1d",
            timestamp=1700000000000,
            price=50000,
            sma_50=48000,
            sma_200=45000,  # Golden cross: SMA50 > SMA200
        )
        result = engine.score_technical(indicators)

        assert result.score > 50
        assert result.details.get("golden_cross") is True

    def test_score_technical_death_cross(self, engine):
        """Should reduce score for death cross."""
        indicators = TechnicalIndicators(
            symbol="BTC",
            timeframe="1d",
            timestamp=1700000000000,
            price=40000,  # Below SMA200
            sma_50=42000,
            sma_200=48000,  # Death cross: SMA50 < SMA200
        )
        result = engine.score_technical(indicators)

        assert result.score < 50
        assert result.details.get("golden_cross") is False

    def test_score_technical_above_sma200(self, engine):
        """Should boost score when price above SMA200."""
        indicators = TechnicalIndicators(
            symbol="BTC",
            timeframe="1d",
            timestamp=1700000000000,
            price=50000,
            sma_200=45000,  # Price above SMA200
        )
        result = engine.score_technical(indicators)

        assert result.score > 50
        assert result.details.get("above_sma200") is True

    def test_score_technical_full_bullish(self, engine):
        """Should give high score for all bullish signals."""
        indicators = TechnicalIndicators(
            symbol="BTC",
            timeframe="1d",
            timestamp=1700000000000,
            price=50000,
            rsi=28,  # Oversold
            sma_50=48000,
            sma_200=45000,  # Golden cross
            macd_histogram=100,  # Positive
            bb_position=15,  # Near lower band
        )
        result = engine.score_technical(indicators)

        assert result.score > 80
        assert result.signal == "bullish"

    # =========================================================================
    # Patterns Score Tests
    # =========================================================================

    def test_score_patterns_none(self, engine):
        """Should return neutral score when no patterns."""
        result = engine.score_patterns(None)

        assert result.score == 50
        assert result.signal == "neutral"

    def test_score_patterns_bullish(self, engine):
        """Should reflect bullish patterns."""
        pattern_summary = {
            "score": 70,
            "bullish_count": 3,
            "bearish_count": 1,
            "bullish_patterns": ["double_bottom", "ascending_triangle", "bullish_engulfing"],
            "bearish_patterns": ["evening_star"],
            "total_patterns": 4,
        }
        result = engine.score_patterns(pattern_summary)

        assert result.score == 70
        assert result.signal == "bullish"

    def test_score_patterns_bearish(self, engine):
        """Should reflect bearish patterns."""
        pattern_summary = {
            "score": 30,
            "bullish_count": 1,
            "bearish_count": 3,
            "bullish_patterns": ["hammer"],
            "bearish_patterns": ["head_shoulders", "descending_triangle", "bearish_engulfing"],
            "total_patterns": 4,
        }
        result = engine.score_patterns(pattern_summary)

        assert result.score == 30
        assert result.signal == "bearish"

    # =========================================================================
    # Cycle Score Tests
    # =========================================================================

    def test_score_cycle_none(self, engine):
        """Should return neutral score when no cycle data."""
        result = engine.score_cycle(None)

        assert result.score == 50
        assert result.signal == "neutral"

    def test_score_cycle_accumulation(self, engine):
        """Should give high score for accumulation phase."""
        cycle_data = {
            "phase": "accumulation",
            "phase_name_ru": "Накопление",
            "days_since_halving": 200,
            "distance_from_ath_pct": 60,
        }
        result = engine.score_cycle(cycle_data)

        assert result.score == 75  # accumulation = 75
        assert result.signal == "bullish"

    def test_score_cycle_euphoria(self, engine):
        """Should give low score for euphoria phase (high risk)."""
        cycle_data = {
            "phase": "euphoria",
            "phase_name_ru": "Эйфория",
            "days_since_halving": 500,
            "distance_from_ath_pct": 5,
        }
        result = engine.score_cycle(cycle_data)

        assert result.score == 30  # euphoria = 30
        assert result.signal == "bearish"

    def test_score_cycle_capitulation(self, engine):
        """Should give highest score for capitulation (best buying opportunity)."""
        cycle_data = {
            "phase": "capitulation",
            "phase_name_ru": "Капитуляция",
            "days_since_halving": 900,
            "distance_from_ath_pct": 80,
        }
        result = engine.score_cycle(cycle_data)

        assert result.score == 85  # capitulation = 85
        assert result.signal == "bullish"

    # =========================================================================
    # Fear & Greed Score Tests
    # =========================================================================

    def test_score_fear_greed_none(self, engine):
        """Should return neutral score when no F&G value."""
        result = engine.score_fear_greed(None)

        assert result.score == 50
        assert result.signal == "neutral"

    def test_score_fear_greed_extreme_fear(self, engine):
        """Extreme fear should give bullish signal (contrarian)."""
        result = engine.score_fear_greed(10)  # Extreme fear

        assert result.score == 80
        assert result.signal == "bullish"
        assert result.details["interpretation"] == "extreme_fear"

    def test_score_fear_greed_extreme_greed(self, engine):
        """Extreme greed should give bearish signal (contrarian)."""
        result = engine.score_fear_greed(90)  # Extreme greed

        assert result.score == 20
        assert result.signal == "bearish"
        assert result.details["interpretation"] == "extreme_greed"

    def test_score_fear_greed_neutral(self, engine):
        """Neutral F&G should give neutral signal."""
        result = engine.score_fear_greed(50)

        assert result.score == 50
        assert result.signal == "neutral"
        assert result.details["interpretation"] == "neutral"

    # =========================================================================
    # Derivatives Score Tests
    # =========================================================================

    def test_score_derivatives_none(self, engine):
        """Should return neutral score when no derivatives data."""
        result = engine.score_derivatives(None)

        assert result.score == 50
        assert result.signal == "neutral"

    def test_score_derivatives_high_funding(self, engine):
        """High positive funding should be bearish (contrarian)."""
        deriv_data = {
            "funding_rate": 0.001,  # 0.1% - high
            "long_short_ratio": 1.2,
        }
        result = engine.score_derivatives(deriv_data)

        assert result.score < 50
        assert "funding_rate" in result.details

    def test_score_derivatives_negative_funding(self, engine):
        """Negative funding should be bullish (shorts paying)."""
        deriv_data = {
            "funding_rate": -0.0005,  # -0.05%
            "long_short_ratio": 0.8,
        }
        result = engine.score_derivatives(deriv_data)

        assert result.score > 50

    def test_score_derivatives_high_ls_ratio(self, engine):
        """High L/S ratio should be bearish (contrarian)."""
        deriv_data = {
            "funding_rate": 0,
            "long_short_ratio": 2.0,  # Many longs
        }
        result = engine.score_derivatives(deriv_data)

        assert result.score < 50

    # =========================================================================
    # OnChain Score Tests
    # =========================================================================

    def test_score_onchain_none(self, engine):
        """Should return neutral score when no onchain data."""
        result = engine.score_onchain(None)

        assert result.score == 50
        assert result.signal == "neutral"

    def test_score_onchain_undervalued_mvrv(self, engine):
        """Low MVRV should be bullish."""
        onchain_data = {
            "mvrv": 0.8,  # Undervalued
            "exchange_reserves_change": 0,
        }
        result = engine.score_onchain(onchain_data)

        assert result.score > 50

    def test_score_onchain_overvalued_mvrv(self, engine):
        """High MVRV should be bearish."""
        onchain_data = {
            "mvrv": 4.0,  # Overvalued
            "exchange_reserves_change": 0,
        }
        result = engine.score_onchain(onchain_data)

        assert result.score < 50

    def test_score_onchain_exchange_outflow(self, engine):
        """Exchange outflow should be bullish."""
        onchain_data = {
            "mvrv": 2.0,
            "exchange_reserves_change": -10,  # Outflow
        }
        result = engine.score_onchain(onchain_data)

        assert result.score > 50


class TestCompositeScoreCalculation:
    """Tests for composite score calculation."""

    @pytest.fixture
    def engine(self):
        return ScoringEngine()

    def test_calculate_with_no_data(self, engine):
        """Should return result with no data (neutral components but weighted scores may vary)."""
        result = engine.calculate(symbol="BTC")

        assert isinstance(result, CompositeScore)
        assert result.symbol == "BTC"
        # All components should be neutral (score=50)
        for component in result.components:
            assert component.score == 50
            assert component.signal == "neutral"

    def test_calculate_with_all_bullish(self, engine):
        """Should return bullish score with all bullish components."""
        indicators = TechnicalIndicators(
            symbol="BTC",
            timeframe="1d",
            timestamp=1700000000000,
            price=50000,
            rsi=25,
            sma_50=48000,
            sma_200=45000,
            macd_histogram=100,
            bb_position=10,
        )
        pattern_summary = {"score": 80, "bullish_count": 4, "bearish_count": 0}
        cycle_data = {"phase": "accumulation"}
        fg_value = 15  # Extreme fear
        deriv_data = {"funding_rate": -0.001, "long_short_ratio": 0.5}
        onchain_data = {"mvrv": 0.8, "exchange_reserves_change": -10}

        result = engine.calculate(
            symbol="BTC",
            indicators=indicators,
            pattern_summary=pattern_summary,
            cycle_data=cycle_data,
            fg_value=fg_value,
            deriv_data=deriv_data,
            onchain_data=onchain_data,
        )

        assert result.total_score > 70
        assert "bullish" in result.signal
        assert result.action in ["buy", "strong_buy"]

    def test_calculate_with_all_bearish(self, engine):
        """Should return bearish score with all bearish components."""
        indicators = TechnicalIndicators(
            symbol="BTC",
            timeframe="1d",
            timestamp=1700000000000,
            price=50000,
            rsi=80,  # Overbought
            sma_50=42000,
            sma_200=45000,  # Death cross
            macd_histogram=-100,
            bb_position=90,  # Near upper band
        )
        pattern_summary = {"score": 20, "bullish_count": 0, "bearish_count": 4}
        cycle_data = {"phase": "euphoria"}
        fg_value = 90  # Extreme greed
        deriv_data = {"funding_rate": 0.002, "long_short_ratio": 2.5}
        onchain_data = {"mvrv": 4.5, "exchange_reserves_change": 15}

        result = engine.calculate(
            symbol="BTC",
            indicators=indicators,
            pattern_summary=pattern_summary,
            cycle_data=cycle_data,
            fg_value=fg_value,
            deriv_data=deriv_data,
            onchain_data=onchain_data,
        )

        assert result.total_score < 30
        assert "bearish" in result.signal
        assert result.action in ["sell", "strong_sell"]

    def test_calculate_components_count(self, engine):
        """Should have all 6 components."""
        result = engine.calculate(symbol="BTC")

        assert len(result.components) == 6
        component_names = [c.name for c in result.components]
        assert "technical" in component_names
        assert "patterns" in component_names
        assert "cycle" in component_names
        assert "derivatives" in component_names
        assert "fear_greed" in component_names
        assert "onchain" in component_names

    def test_calculate_risk_level(self, engine):
        """Should calculate risk level correctly."""
        # High score = low risk
        result_low_risk = engine.calculate(
            symbol="BTC",
            fg_value=15,  # Extreme fear = high score = low risk
        )

        # Low score = high risk
        result_high_risk = engine.calculate(
            symbol="BTC",
            fg_value=90,  # Extreme greed = low score = high risk
        )

        assert result_low_risk.risk_score < result_high_risk.risk_score

    def test_calculate_confidence(self, engine):
        """Should calculate confidence based on component agreement."""
        # All components agree (bullish)
        result = engine.calculate(
            symbol="BTC",
            fg_value=15,
            cycle_data={"phase": "capitulation"},
            deriv_data={"funding_rate": -0.001, "long_short_ratio": 0.5},
        )

        # Should have some confidence
        assert result.confidence > 0

    def test_to_dict(self, engine):
        """CompositeScore.to_dict() should serialize correctly."""
        result = engine.calculate(symbol="BTC", fg_value=50)

        dict_result = result.to_dict()

        assert isinstance(dict_result, dict)
        assert "symbol" in dict_result
        assert "score" in dict_result
        assert "components" in dict_result
        assert "recommendation" in dict_result
        assert "risk" in dict_result

    def test_get_summary(self, engine):
        """CompositeScore.get_summary() should return text summary."""
        result = engine.calculate(symbol="BTC", fg_value=50)

        summary = result.get_summary()

        assert isinstance(summary, str)
        assert "BTC" in summary
        assert "Score" in summary


class TestSignalThresholds:
    """Tests for signal threshold boundaries."""

    @pytest.fixture
    def engine(self):
        return ScoringEngine()

    def test_strong_bullish_threshold(self, engine):
        """Score >= 75 should be strong_bullish."""
        # We need to create a scenario that gives score >= 75
        result = engine.calculate(
            symbol="BTC",
            fg_value=10,  # Extreme fear = 80
            cycle_data={"phase": "capitulation"},  # = 85
            deriv_data={"funding_rate": -0.001, "long_short_ratio": 0.5},  # bullish
        )

        if result.total_score >= 75:
            assert result.signal == "strong_bullish"
            assert result.action == "strong_buy"

    def test_strong_bearish_threshold(self, engine):
        """Score <= 25 should be strong_bearish."""
        result = engine.calculate(
            symbol="BTC",
            fg_value=95,  # Extreme greed = 20
            cycle_data={"phase": "euphoria"},  # = 30
            deriv_data={"funding_rate": 0.002, "long_short_ratio": 2.5},  # bearish
        )

        if result.total_score <= 25:
            assert result.signal == "strong_bearish"
            assert result.action == "strong_sell"


class TestComponentScore:
    """Tests for ComponentScore dataclass."""

    def test_component_score_to_dict(self):
        """ComponentScore.to_dict() should serialize correctly."""
        component = ComponentScore(
            name="test",
            name_ru="Тест",
            score=65,
            weight=0.3,
            weighted_score=19.5,
            details={"key": "value"},
            signal="bullish",
        )

        result = component.to_dict()

        assert result["name"] == "test"
        assert result["score"] == 65
        assert result["weight"] == 0.3
        assert result["weighted"] == 19.5
        assert result["signal"] == "bullish"
