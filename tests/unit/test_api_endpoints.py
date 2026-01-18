"""
Unit tests for API endpoints.

Tests cover:
- Analysis endpoints
- Health endpoint
- Error handling
- Response structures
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAnalysisEndpoints:
    """Tests for /api/analysis endpoints."""

    @pytest.fixture
    def mock_onchain_analyzer(self):
        """Mock OnChainAnalyzer."""
        with patch("api.routes.analysis.OnChainAnalyzer") as mock:
            analyzer = AsyncMock()
            analyzer.analyze = AsyncMock()
            analyzer.close = AsyncMock()
            analyzer.fetch_fear_greed = AsyncMock()
            analyzer.get_fear_greed_signal = MagicMock(
                return_value={
                    "signal": "neutral",
                    "description": "Neutral market",
                    "score_adjustment": 0,
                }
            )
            mock.return_value = analyzer
            yield analyzer

    @pytest.fixture
    def mock_derivatives_analyzer(self):
        """Mock DerivativesAnalyzer."""
        with patch("api.routes.analysis.DerivativesAnalyzer") as mock:
            analyzer = AsyncMock()
            analyzer.analyze = AsyncMock()
            analyzer.close = AsyncMock()
            mock.return_value = analyzer
            yield analyzer

    @pytest.fixture
    def mock_cycle_detector(self):
        """Mock CycleDetector."""
        with patch("api.routes.analysis.CycleDetector") as mock:
            detector = MagicMock()
            cycle_info = MagicMock()
            cycle_info.to_dict.return_value = {
                "phase": "accumulation",
                "phase_name": "Accumulation",
                "recommendation": "Good time for DCA",
            }
            detector.detect_cycle.return_value = cycle_info
            mock.return_value = detector
            yield detector

    @pytest.fixture
    def mock_scoring_engine(self):
        """Mock ScoringEngine."""
        with patch("api.routes.analysis.ScoringEngine") as mock:
            engine = MagicMock()
            score = MagicMock()
            score.to_dict.return_value = {
                "symbol": "BTC",
                "score": {"total": 65, "signal": "bullish"},
                "recommendation": {"action": "buy"},
            }
            engine.calculate.return_value = score
            mock.return_value = engine
            yield engine


class TestGetAnalysis:
    """Tests for GET /api/analysis/{symbol}."""

    @pytest.mark.asyncio
    async def test_get_analysis_returns_dict(self):
        """Should return dictionary response."""
        from api.routes.analysis import get_analysis

        with (
            patch("api.routes.analysis.OnChainAnalyzer") as mock_onchain,
            patch("api.routes.analysis.DerivativesAnalyzer") as mock_deriv,
            patch("api.routes.analysis.CycleDetector") as mock_cycle,
        ):
            # Setup mocks
            onchain_analyzer = AsyncMock()
            onchain_data = MagicMock()
            onchain_data.to_dict.return_value = {"fear_greed": {"value": 50}}
            onchain_analyzer.analyze.return_value = onchain_data
            onchain_analyzer.close = AsyncMock()
            mock_onchain.return_value = onchain_analyzer

            deriv_analyzer = AsyncMock()
            deriv_data = MagicMock()
            deriv_data.to_dict.return_value = {"funding": {"rate": 0.0001}}
            deriv_analyzer.analyze.return_value = deriv_data
            deriv_analyzer.close = AsyncMock()
            mock_deriv.return_value = deriv_analyzer

            cycle_detector = MagicMock()
            cycle_info = MagicMock()
            cycle_info.to_dict.return_value = {"phase": "accumulation"}
            cycle_detector.detect_cycle.return_value = cycle_info
            mock_cycle.return_value = cycle_detector

            result = await get_analysis("BTC")

            assert isinstance(result, dict)
            assert result["symbol"] == "BTC"
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_analysis_uppercase_symbol(self):
        """Should convert symbol to uppercase."""
        from api.routes.analysis import get_analysis

        with (
            patch("api.routes.analysis.OnChainAnalyzer") as mock_onchain,
            patch("api.routes.analysis.DerivativesAnalyzer") as mock_deriv,
            patch("api.routes.analysis.CycleDetector"),
        ):
            onchain_analyzer = AsyncMock()
            onchain_analyzer.analyze.return_value = MagicMock(to_dict=MagicMock(return_value={}))
            onchain_analyzer.close = AsyncMock()
            mock_onchain.return_value = onchain_analyzer

            deriv_analyzer = AsyncMock()
            deriv_analyzer.analyze.return_value = MagicMock(to_dict=MagicMock(return_value={}))
            deriv_analyzer.close = AsyncMock()
            mock_deriv.return_value = deriv_analyzer

            result = await get_analysis("btc")

            assert result["symbol"] == "BTC"


class TestGetScore:
    """Tests for GET /api/analysis/{symbol}/score."""

    @pytest.mark.asyncio
    async def test_get_score_returns_dict(self):
        """Should return score dictionary."""
        from api.routes.analysis import get_score

        with (
            patch("api.routes.analysis.ScoringEngine") as mock_scoring,
            patch("api.routes.analysis.OnChainAnalyzer") as mock_onchain,
            patch("api.routes.analysis.DerivativesAnalyzer") as mock_deriv,
            patch("api.routes.analysis.CycleDetector") as mock_cycle,
        ):
            # Setup ScoringEngine mock
            engine = MagicMock()
            score_result = MagicMock()
            score_result.to_dict.return_value = {
                "symbol": "BTC",
                "score": {"total": 65},
            }
            engine.calculate.return_value = score_result
            mock_scoring.return_value = engine

            # Setup OnChainAnalyzer mock
            onchain_analyzer = AsyncMock()
            onchain_data = MagicMock()
            onchain_data.fear_greed = MagicMock(value=50)
            onchain_analyzer.analyze.return_value = onchain_data
            onchain_analyzer.close = AsyncMock()
            mock_onchain.return_value = onchain_analyzer

            # Setup DerivativesAnalyzer mock
            deriv_analyzer = AsyncMock()
            deriv_data = MagicMock()
            deriv_data.funding = MagicMock(rate=0.0001)
            deriv_data.long_short = MagicMock(long_short_ratio=1.2)
            deriv_analyzer.analyze.return_value = deriv_data
            deriv_analyzer.close = AsyncMock()
            mock_deriv.return_value = deriv_analyzer

            # Setup CycleDetector mock
            cycle_detector = MagicMock()
            cycle_info = MagicMock()
            cycle_info.phase = MagicMock(value="accumulation")
            cycle_info.phase_name_ru = "Накопление"
            cycle_info.days_since_halving = 200
            cycle_info.distance_from_ath_pct = 50
            cycle_detector.detect_cycle.return_value = cycle_info
            mock_cycle.return_value = cycle_detector

            result = await get_score("BTC")

            assert isinstance(result, dict)
            assert "symbol" in result


class TestGetMarketSummary:
    """Tests for GET /api/market/summary."""

    @pytest.mark.asyncio
    async def test_get_market_summary_structure(self):
        """Should return proper structure."""
        from api.routes.analysis import get_market_summary

        with (
            patch("api.routes.analysis.OnChainAnalyzer") as mock_onchain,
            patch("api.routes.analysis.DerivativesAnalyzer") as mock_deriv,
            patch("api.routes.analysis.CycleDetector") as mock_cycle,
            patch("api.routes.analysis.get_symbols", return_value=["BTC", "ETH"]),
        ):
            # Setup OnChainAnalyzer mock
            onchain_analyzer = AsyncMock()
            onchain_data = MagicMock()
            fg_data = MagicMock()
            fg_data.to_dict.return_value = {"value": 50, "classification": "Neutral"}
            onchain_data.fear_greed = fg_data
            onchain_data.network = None
            onchain_analyzer.analyze.return_value = onchain_data
            onchain_analyzer.close = AsyncMock()
            mock_onchain.return_value = onchain_analyzer

            # Setup DerivativesAnalyzer mock
            deriv_analyzer = AsyncMock()
            deriv_data = MagicMock()
            deriv_data.funding = MagicMock(rate=0.0001)
            deriv_data.long_short = MagicMock(long_short_ratio=1.2)
            deriv_data.signal = "neutral"
            deriv_analyzer.analyze.return_value = deriv_data
            deriv_analyzer.close = AsyncMock()
            mock_deriv.return_value = deriv_analyzer

            # Setup CycleDetector mock
            cycle_detector = MagicMock()
            cycle_info = MagicMock()
            cycle_info.phase = MagicMock(value="accumulation")
            cycle_info.phase_name = "Accumulation"
            cycle_info.recommendation = "Good time for DCA"
            cycle_info.risk_level = "low"
            cycle_info.days_since_halving = 200
            cycle_info.days_to_next_halving = 1260
            cycle_detector.detect_cycle.return_value = cycle_info
            mock_cycle.return_value = cycle_detector

            result = await get_market_summary()

            assert isinstance(result, dict)
            assert "timestamp" in result
            assert "symbols" in result
            assert "fear_greed" in result
            assert "btc_cycle" in result
            assert "derivatives" in result


class TestGetFearGreed:
    """Tests for GET /api/market/fear-greed."""

    @pytest.mark.asyncio
    async def test_get_fear_greed_success(self):
        """Should return F&G data on success."""
        from api.routes.analysis import get_fear_greed

        with patch("api.routes.analysis.OnChainAnalyzer") as mock_onchain:
            analyzer = AsyncMock()
            fg_data = MagicMock()
            fg_data.value = 50
            fg_data.classification = "Neutral"
            fg_data.timestamp = "2024-01-01"
            analyzer.fetch_fear_greed.return_value = fg_data
            # get_fear_greed_signal is a sync method, so use MagicMock
            analyzer.get_fear_greed_signal = MagicMock(
                return_value={
                    "signal": "neutral",
                    "description": "Neutral market",
                    "score_adjustment": 0,
                }
            )
            analyzer.close = AsyncMock()
            mock_onchain.return_value = analyzer

            result = await get_fear_greed()

            assert isinstance(result, dict)
            assert "value" in result
            assert result["value"] == 50
            assert "classification" in result
            assert "signal" in result

    @pytest.mark.asyncio
    async def test_get_fear_greed_unavailable(self):
        """Should raise HTTPException when F&G unavailable."""
        from fastapi import HTTPException

        from api.routes.analysis import get_fear_greed

        with patch("api.routes.analysis.OnChainAnalyzer") as mock_onchain:
            analyzer = AsyncMock()
            analyzer.fetch_fear_greed.return_value = None
            analyzer.close = AsyncMock()
            mock_onchain.return_value = analyzer

            with pytest.raises(HTTPException) as exc_info:
                await get_fear_greed()

            assert exc_info.value.status_code == 503


class TestTriggerAnalysis:
    """Tests for POST /api/analysis/trigger."""

    @pytest.mark.asyncio
    async def test_trigger_analysis_default_symbols(self):
        """Should use default symbols when none provided."""
        from api.routes.analysis import trigger_analysis

        with patch("api.routes.analysis.get_symbols", return_value=["BTC", "ETH"]):
            result = await trigger_analysis(symbols=None)

            assert result["status"] == "triggered"
            assert result["symbols"] == ["BTC", "ETH"]

    @pytest.mark.asyncio
    async def test_trigger_analysis_custom_symbols(self):
        """Should use provided symbols."""
        from api.routes.analysis import trigger_analysis

        result = await trigger_analysis(symbols=["SOL", "TON"])

        assert result["status"] == "triggered"
        assert result["symbols"] == ["SOL", "TON"]

    @pytest.mark.asyncio
    async def test_trigger_analysis_has_timestamp(self):
        """Should include timestamp."""
        from api.routes.analysis import trigger_analysis

        result = await trigger_analysis(symbols=["BTC"])

        assert "timestamp" in result


class TestGetSymbols:
    """Tests for get_symbols helper function."""

    def test_get_symbols_from_env(self):
        """Should parse symbols from environment."""
        from api.routes.analysis import get_symbols

        with patch.dict("os.environ", {"HA_SYMBOLS": "BTC/USDT, ETH/USDT, SOL/USDT"}):
            result = get_symbols()

            assert "BTC" in result
            assert "ETH" in result
            assert "SOL" in result

    def test_get_symbols_default(self):
        """Should return defaults when env not set."""
        from api.routes.analysis import get_symbols

        with patch.dict("os.environ", {}, clear=True):
            result = get_symbols()

            assert isinstance(result, list)
            assert len(result) > 0


class TestErrorHandling:
    """Tests for error handling in endpoints."""

    @pytest.mark.asyncio
    async def test_get_analysis_handles_exception(self):
        """Should raise HTTPException on error."""
        from fastapi import HTTPException

        from api.routes.analysis import get_analysis

        with patch("api.routes.analysis.OnChainAnalyzer") as mock:
            mock.side_effect = Exception("Test error")

            with pytest.raises(HTTPException) as exc_info:
                await get_analysis("BTC")

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_score_handles_exception(self):
        """Should raise HTTPException on error."""
        from fastapi import HTTPException

        from api.routes.analysis import get_score

        with patch("api.routes.analysis.ScoringEngine") as mock:
            mock.side_effect = Exception("Test error")

            with pytest.raises(HTTPException) as exc_info:
                await get_score("BTC")

            assert exc_info.value.status_code == 500


class TestHealthEndpoint:
    """Tests for health endpoint."""

    def test_health_module_exists(self):
        """Health module should be importable."""
        from api.routes import health

        assert health is not None

    def test_health_router_exists(self):
        """Health router should exist."""
        from api.routes.health import router

        assert router is not None


class TestDerivativesEndpoint:
    """Tests for GET /api/analysis/{symbol}/derivatives."""

    @pytest.mark.asyncio
    async def test_get_derivatives_success(self):
        """Should return derivatives data."""
        from api.routes.analysis import get_derivatives

        with patch("api.routes.analysis.DerivativesAnalyzer") as mock:
            analyzer = AsyncMock()
            deriv_data = MagicMock()
            deriv_data.to_dict.return_value = {
                "symbol": "BTC",
                "funding": {"rate": 0.0001},
                "long_short": {"ratio": 1.2},
            }
            analyzer.analyze.return_value = deriv_data
            analyzer.close = AsyncMock()
            mock.return_value = analyzer

            result = await get_derivatives("BTC")

            assert isinstance(result, dict)
            assert "funding" in result

    @pytest.mark.asyncio
    async def test_get_derivatives_error(self):
        """Should raise HTTPException on error."""
        from fastapi import HTTPException

        from api.routes.analysis import get_derivatives

        with patch("api.routes.analysis.DerivativesAnalyzer") as mock:
            analyzer = AsyncMock()
            analyzer.analyze.side_effect = Exception("API error")
            analyzer.close = AsyncMock()
            mock.return_value = analyzer

            with pytest.raises(HTTPException) as exc_info:
                await get_derivatives("BTC")

            assert exc_info.value.status_code == 500
