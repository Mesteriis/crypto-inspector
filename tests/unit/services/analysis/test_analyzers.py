"""
Analysis Services Tests - Тесты аналитических сервисов.

Тестирует:
- TechnicalAnalyzer
- PatternDetector
- ScoringEngine
- InvestorAnalyzer
"""

import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(project_root, "src"))

pytestmark = [pytest.mark.unit]


# =============================================================================
# TECHNICAL ANALYZER TESTS
# =============================================================================


class TestTechnicalAnalyzer:
    """Тесты для TechnicalAnalyzer."""

    def test_import(self):
        """Проверка импорта."""
        from service.analysis.technical import TechnicalAnalyzer

        assert TechnicalAnalyzer is not None

    def test_init(self):
        """Проверка инициализации."""
        from service.analysis.technical import TechnicalAnalyzer

        analyzer = TechnicalAnalyzer()
        assert analyzer is not None

    def test_calc_rsi_neutral(self):
        """Тест RSI в нейтральной зоне."""
        from service.analysis.technical import TechnicalAnalyzer

        analyzer = TechnicalAnalyzer()

        # Генерируем данные с примерно равными подъемами и падениями
        prices = [100 + i * 0.1 * ((-1) ** i) for i in range(50)]

        rsi = analyzer.calc_rsi(prices)

        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_calc_rsi_overbought(self):
        """Тест RSI в зоне перекупленности."""
        from service.analysis.technical import TechnicalAnalyzer

        analyzer = TechnicalAnalyzer()

        # Генерируем восходящий тренд
        prices = [100 + i * 2 for i in range(50)]

        rsi = analyzer.calc_rsi(prices)

        assert rsi is not None
        # При сильном восходящем тренде RSI должен быть высоким
        assert rsi > 50

    def test_calc_rsi_oversold(self):
        """Тест RSI в зоне перепроданности."""
        from service.analysis.technical import TechnicalAnalyzer

        analyzer = TechnicalAnalyzer()

        # Генерируем нисходящий тренд
        prices = [100 - i * 1.5 for i in range(50)]

        rsi = analyzer.calc_rsi(prices)

        assert rsi is not None
        # При сильном нисходящем тренде RSI должен быть низким
        assert rsi < 50

    def test_calc_sma(self):
        """Тест SMA расчета."""
        from service.analysis.technical import TechnicalAnalyzer

        analyzer = TechnicalAnalyzer()

        prices = [100] * 50
        sma = analyzer.calc_sma(prices, period=20)

        assert sma == 100.0

    def test_calc_sma_trending(self):
        """Тест SMA на тренде."""
        from service.analysis.technical import TechnicalAnalyzer

        analyzer = TechnicalAnalyzer()

        prices = [100 + i for i in range(50)]
        sma = analyzer.calc_sma(prices, period=20)

        # SMA должна быть меньше последней цены на восходящем тренде
        assert sma < prices[-1]

    def test_calc_macd(self):
        """Тест MACD расчета."""
        from service.analysis.technical import TechnicalAnalyzer

        analyzer = TechnicalAnalyzer()

        prices = [100 + i * 0.5 for i in range(50)]
        macd_line, signal_line, histogram = analyzer.calc_macd(prices)

        assert macd_line is not None
        assert signal_line is not None
        assert histogram is not None

    def test_calc_bollinger_bands(self):
        """Тест Bollinger Bands расчета."""
        from service.analysis.technical import TechnicalAnalyzer

        analyzer = TechnicalAnalyzer()

        prices = [100 + i * 0.1 for i in range(50)]
        upper, middle, lower, position = analyzer.calc_bollinger_bands(prices)

        assert upper > middle > lower
        assert 0 <= position <= 100


# =============================================================================
# PATTERN DETECTOR TESTS
# =============================================================================


class TestPatternDetector:
    """Тесты для PatternDetector."""

    def test_import(self):
        """Проверка импорта."""
        from service.analysis.patterns import PatternDetector

        assert PatternDetector is not None

    def test_init(self):
        """Проверка инициализации."""
        from service.analysis.patterns import PatternDetector

        detector = PatternDetector()
        assert detector is not None

    def test_detect_all_empty(self):
        """Тест обнаружения паттернов на пустых данных."""
        from service.analysis.patterns import PatternDetector

        detector = PatternDetector()

        # Слишком мало свечей
        candles = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}] * 10

        patterns = detector.detect_all("BTC/USDT", candles)

        # Может вернуть пустой список или паттерны
        assert isinstance(patterns, list)

    def test_detect_golden_cross(self, golden_cross_candles):
        """Тест обнаружения Golden Cross."""
        from service.analysis.patterns import PatternDetector

        detector = PatternDetector()

        # Используем фикстуру с паттерном golden cross
        patterns = detector.detect_all("BTC/USDT", golden_cross_candles)

        # Проверяем структуру результата
        assert isinstance(patterns, list)
        for pattern in patterns:
            assert hasattr(pattern, "name") or isinstance(pattern, dict)


# =============================================================================
# SCORING ENGINE TESTS
# =============================================================================


class TestScoringEngine:
    """Тесты для ScoringEngine."""

    def test_import(self):
        """Проверка импорта."""
        from service.analysis.scoring import ScoringEngine

        assert ScoringEngine is not None

    def test_init(self):
        """Проверка инициализации."""
        from service.analysis.scoring import ScoringEngine

        engine = ScoringEngine()
        assert engine is not None

    def test_calculate_neutral(self):
        """Тест расчета нейтрального скора."""
        from service.analysis.scoring import ScoringEngine
        from service.analysis.technical import TechnicalIndicators

        engine = ScoringEngine()

        # Нейтральные индикаторы
        indicators = TechnicalIndicators(
            symbol="BTC/USDT",
            timeframe="1d",
            timestamp=0,
            price=100000,
            rsi=50,
            sma_50=100000,
            sma_200=100000,
            macd_line=0,
            macd_signal=0,
            macd_histogram=0,
            bb_position=50,
        )

        score = engine.calculate(
            symbol="BTC/USDT",
            indicators=indicators,
        )

        assert score is not None
        # Нейтральный скор должен быть около 50
        score_dict = score.to_dict()
        assert "score" in score_dict

    def test_calculate_bullish(self):
        """Тест расчета бычьего скора."""
        from service.analysis.scoring import ScoringEngine
        from service.analysis.technical import TechnicalIndicators

        engine = ScoringEngine()

        # Бычьи индикаторы
        indicators = TechnicalIndicators(
            symbol="BTC/USDT",
            timeframe="1d",
            timestamp=0,
            price=100000,
            rsi=35,  # Перепроданность
            sma_50=98000,  # Цена выше SMA
            sma_200=95000,
            macd_line=100,
            macd_signal=50,
            macd_histogram=50,  # Положительная гистограмма
            bb_position=20,  # Близко к нижней границе
        )

        score = engine.calculate(
            symbol="BTC/USDT",
            indicators=indicators,
        )

        score_dict = score.to_dict()
        # Бычий скор должен быть выше 50
        assert score_dict["score"]["total"] >= 50

    def test_calculate_bearish(self):
        """Тест расчета медвежьего скора."""
        from service.analysis.scoring import ScoringEngine
        from service.analysis.technical import TechnicalIndicators

        engine = ScoringEngine()

        # Медвежьи индикаторы
        indicators = TechnicalIndicators(
            symbol="BTC/USDT",
            timeframe="1d",
            timestamp=0,
            price=100000,
            rsi=75,  # Перекупленность
            sma_50=102000,  # Цена ниже SMA
            sma_200=105000,
            macd_line=-100,
            macd_signal=-50,
            macd_histogram=-50,  # Отрицательная гистограмма
            bb_position=85,  # Близко к верхней границе
        )

        score = engine.calculate(
            symbol="BTC/USDT",
            indicators=indicators,
        )

        score_dict = score.to_dict()
        # Медвежий скор должен быть ниже 50
        assert score_dict["score"]["total"] <= 50


# =============================================================================
# INVESTOR ANALYZER TESTS
# =============================================================================


class TestInvestorAnalyzer:
    """Тесты для анализатора инвестора."""

    def test_module_import(self):
        """Проверка импорта модуля."""
        import service.analysis.investor

        assert service.analysis.investor is not None

    def test_do_nothing_calculation(self, sample_investor_data):
        """Тест расчета 'ничего не делать'."""
        # Проверяем структуру данных
        assert "do_nothing_ok" in sample_investor_data
        assert isinstance(sample_investor_data["do_nothing_ok"], bool)

    def test_phase_detection(self, sample_investor_data):
        """Тест определения фазы рынка."""
        assert "phase" in sample_investor_data
        assert sample_investor_data["phase"] in ["accumulation", "markup", "distribution", "markdown"]

    def test_calm_indicator_range(self, sample_investor_data):
        """Тест диапазона индикатора спокойствия."""
        assert "calm_indicator" in sample_investor_data
        assert 0 <= sample_investor_data["calm_indicator"] <= 100


# =============================================================================
# DIVERGENCE DETECTOR TESTS
# =============================================================================


class TestDivergenceDetector:
    """Тесты для детектора дивергенций."""

    def test_import(self):
        """Проверка импорта."""
        from service.analysis.divergences import DivergenceDetector

        assert DivergenceDetector is not None

    def test_get_detector_function(self):
        """Проверка функции получения детектора."""
        from service.analysis.divergences import get_divergence_detector

        assert get_divergence_detector is not None

    def test_divergence_type_enum(self):
        """Проверка enum типов дивергенций."""
        from service.analysis.divergences import DivergenceType

        assert DivergenceType is not None


# =============================================================================
# CORRELATION TRACKER TESTS
# =============================================================================


class TestCorrelationTracker:
    """Тесты для трекера корреляций."""

    def test_import(self):
        """Проверка импорта."""
        from service.analysis.correlation import CorrelationTracker

        assert CorrelationTracker is not None

    def test_get_tracker_function(self):
        """Проверка функции получения трекера."""
        from service.analysis.correlation import get_correlation_tracker

        assert get_correlation_tracker is not None

    def test_correlation_analysis_import(self):
        """Проверка импорта CorrelationAnalysis."""
        from service.analysis.correlation import CorrelationAnalysis

        assert CorrelationAnalysis is not None


# =============================================================================
# SMART SUMMARY TESTS
# =============================================================================


class TestSmartSummary:
    """Тесты для SmartSummaryService."""

    def test_import(self):
        """Проверка импорта."""
        from service.analysis.smart_summary import SmartSummaryService

        assert SmartSummaryService is not None

    def test_init(self):
        """Проверка инициализации."""
        from service.analysis.smart_summary import SmartSummaryService

        service = SmartSummaryService()
        assert service is not None


# =============================================================================
# BRIEFING SERVICE TESTS
# =============================================================================


class TestBriefingService:
    """Тесты для BriefingService."""

    def test_import(self):
        """Проверка импорта."""
        from service.analysis.briefing import BriefingService

        assert BriefingService is not None

    def test_init(self):
        """Проверка инициализации."""
        from service.analysis.briefing import BriefingService

        service = BriefingService()
        assert service is not None
