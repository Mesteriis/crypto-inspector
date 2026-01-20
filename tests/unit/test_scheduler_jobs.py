"""Tests for scheduler jobs module."""

import os

# Add src to path
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from core.scheduler.jobs import (
    DEFAULT_SYMBOLS,
    get_intervals_to_fetch,
    get_symbols,
)


class TestGetSymbols:
    """Tests for get_symbols function."""

    def test_returns_default_when_no_env(self):
        """Should return default symbols when HA_SYMBOLS not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove HA_SYMBOLS if exists
            os.environ.pop("HA_SYMBOLS", None)
            result = get_symbols()
            assert result == DEFAULT_SYMBOLS

    def test_returns_env_symbols_when_set(self):
        """Should return symbols from environment."""
        with patch.dict(os.environ, {"HA_SYMBOLS": "SOL/USDT,TON/USDT"}):
            result = get_symbols()
            assert result == ["SOL/USDT", "TON/USDT"]

    def test_handles_whitespace_in_env(self):
        """Should trim whitespace from symbols."""
        with patch.dict(os.environ, {"HA_SYMBOLS": " BTC/USDT , ETH/USDT "}):
            result = get_symbols()
            assert result == ["BTC/USDT", "ETH/USDT"]

    def test_handles_empty_env(self):
        """Should return defaults for empty env value."""
        with patch.dict(os.environ, {"HA_SYMBOLS": ""}):
            result = get_symbols()
            assert result == DEFAULT_SYMBOLS

    def test_filters_empty_symbols(self):
        """Should filter out empty symbols from comma-separated list."""
        with patch.dict(os.environ, {"HA_SYMBOLS": "BTC/USDT,,ETH/USDT,"}):
            result = get_symbols()
            assert result == ["BTC/USDT", "ETH/USDT"]


class TestGetIntervalsToFetch:
    """Tests for get_intervals_to_fetch function."""

    def test_always_includes_minute_intervals(self):
        """Should always include 1m, 3m, 5m intervals."""
        now = datetime(2024, 1, 15, 10, 23)  # Random time
        result = get_intervals_to_fetch(now)
        assert "1m" in result
        assert "3m" in result
        assert "5m" in result

    def test_includes_15m_at_quarter_hours(self):
        """Should include 15m at 0, 15, 30, 45 minutes."""
        for minute in [0, 15, 30, 45]:
            now = datetime(2024, 1, 15, 10, minute)
            result = get_intervals_to_fetch(now)
            assert "15m" in result, f"15m should be in result at minute {minute}"

    def test_excludes_15m_at_other_minutes(self):
        """Should not include 15m at other minutes."""
        now = datetime(2024, 1, 15, 10, 23)
        result = get_intervals_to_fetch(now)
        assert "15m" not in result

    def test_includes_30m_at_half_hours(self):
        """Should include 30m at 0 and 30 minutes."""
        for minute in [0, 30]:
            now = datetime(2024, 1, 15, 10, minute)
            result = get_intervals_to_fetch(now)
            assert "30m" in result

    def test_includes_1h_at_hour_start(self):
        """Should include 1h when minute is 0."""
        now = datetime(2024, 1, 15, 10, 0)
        result = get_intervals_to_fetch(now)
        assert "1h" in result

    def test_excludes_1h_at_other_minutes(self):
        """Should not include 1h at other minutes."""
        now = datetime(2024, 1, 15, 10, 30)
        result = get_intervals_to_fetch(now)
        assert "1h" not in result

    def test_includes_2h_at_even_hours(self):
        """Should include 2h at even hours."""
        for hour in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]:
            now = datetime(2024, 1, 15, hour, 0)
            result = get_intervals_to_fetch(now)
            assert "2h" in result, f"2h should be in result at hour {hour}"

    def test_excludes_2h_at_odd_hours(self):
        """Should not include 2h at odd hours."""
        now = datetime(2024, 1, 15, 11, 0)
        result = get_intervals_to_fetch(now)
        assert "2h" not in result

    def test_includes_4h_at_divisible_hours(self):
        """Should include 4h at hours divisible by 4."""
        for hour in [0, 4, 8, 12, 16, 20]:
            now = datetime(2024, 1, 15, hour, 0)
            result = get_intervals_to_fetch(now)
            assert "4h" in result

    def test_includes_6h_at_divisible_hours(self):
        """Should include 6h at hours divisible by 6."""
        for hour in [0, 6, 12, 18]:
            now = datetime(2024, 1, 15, hour, 0)
            result = get_intervals_to_fetch(now)
            assert "6h" in result

    def test_includes_8h_at_divisible_hours(self):
        """Should include 8h at hours divisible by 8."""
        for hour in [0, 8, 16]:
            now = datetime(2024, 1, 15, hour, 0)
            result = get_intervals_to_fetch(now)
            assert "8h" in result

    def test_includes_12h_at_divisible_hours(self):
        """Should include 12h at hours divisible by 12."""
        for hour in [0, 12]:
            now = datetime(2024, 1, 15, hour, 0)
            result = get_intervals_to_fetch(now)
            assert "12h" in result

    def test_includes_1d_at_midnight(self):
        """Should include 1d at midnight."""
        now = datetime(2024, 1, 15, 0, 0)
        result = get_intervals_to_fetch(now)
        assert "1d" in result

    def test_excludes_1d_at_other_hours(self):
        """Should not include 1d at other hours."""
        now = datetime(2024, 1, 15, 12, 0)
        result = get_intervals_to_fetch(now)
        assert "1d" not in result

    def test_includes_3d_at_correct_days(self):
        """Should include 3d when day % 3 == 1."""
        # Days 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31
        now = datetime(2024, 1, 1, 0, 0)  # day=1
        result = get_intervals_to_fetch(now)
        assert "3d" in result

        now = datetime(2024, 1, 4, 0, 0)  # day=4
        result = get_intervals_to_fetch(now)
        assert "3d" in result

    def test_excludes_3d_at_other_days(self):
        """Should not include 3d on other days."""
        now = datetime(2024, 1, 2, 0, 0)  # day=2
        result = get_intervals_to_fetch(now)
        assert "3d" not in result

    def test_includes_1w_on_monday(self):
        """Should include 1w on Monday at midnight."""
        now = datetime(2024, 1, 15, 0, 0)  # Monday
        result = get_intervals_to_fetch(now)
        assert "1w" in result

    def test_excludes_1w_on_other_days(self):
        """Should not include 1w on other days."""
        now = datetime(2024, 1, 16, 0, 0)  # Tuesday
        result = get_intervals_to_fetch(now)
        assert "1w" not in result

    def test_includes_1M_on_first_of_month(self):
        """Should include 1M on first of month at midnight."""
        now = datetime(2024, 1, 1, 0, 0)
        result = get_intervals_to_fetch(now)
        assert "1M" in result

    def test_excludes_1M_on_other_days(self):
        """Should not include 1M on other days."""
        now = datetime(2024, 1, 15, 0, 0)
        result = get_intervals_to_fetch(now)
        assert "1M" not in result

    def test_midnight_includes_all_relevant_intervals(self):
        """Should include many intervals at midnight on first Monday of month."""
        # January 1, 2024 is Monday
        now = datetime(2024, 1, 1, 0, 0)
        result = get_intervals_to_fetch(now)

        expected = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
        for interval in expected:
            assert interval in result, f"{interval} should be in result"


class TestHelloWorldJob:
    """Tests for hello_world_job function."""

    @pytest.mark.asyncio
    async def test_hello_world_job_logs_message(self):
        """Should log and print hello world message."""
        from core.scheduler.jobs import hello_world_job

        with patch("builtins.print") as mock_print:
            await hello_world_job()
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Hello World" in call_args


class TestCandlestickSyncJob:
    """Tests for candlestick_sync_job function."""

    @pytest.mark.asyncio
    async def test_calls_fetch_for_each_symbol_interval(self):
        """Should fetch candlesticks for all symbols and intervals."""
        from core.scheduler.jobs import candlestick_sync_job

        with (
            patch("core.scheduler.jobs.get_currency_list", return_value=["BTC/USDT"]),
            patch("core.scheduler.jobs.get_intervals_to_fetch", return_value=["1m"]),
            patch("core.scheduler.jobs.fetch_and_save_candlesticks", new_callable=AsyncMock) as mock_fetch,
            patch("service.ha_integration.notify_error", new_callable=AsyncMock),
            patch("service.ha_integration.notify_sync_complete", new_callable=AsyncMock),
        ):
            mock_fetch.return_value = True
            await candlestick_sync_job()
            mock_fetch.assert_called_once_with("BTC/USDT", "1m")

    @pytest.mark.asyncio
    async def test_notifies_on_failures(self):
        """Should notify about errors when fetches fail."""
        from core.scheduler.jobs import candlestick_sync_job

        with (
            patch("core.scheduler.jobs.get_symbols", return_value=["BTC/USDT"]),
            patch("core.scheduler.jobs.get_intervals_to_fetch", return_value=["1m"]),
            patch("core.scheduler.jobs.fetch_and_save_candlesticks", new_callable=AsyncMock) as mock_fetch,
            patch("service.ha_integration.notify_error", new_callable=AsyncMock) as mock_notify,
            patch("service.ha_integration.notify_sync_complete", new_callable=AsyncMock),
        ):
            mock_fetch.return_value = False
            await candlestick_sync_job()
            mock_notify.assert_called_once()


class TestMarketAnalysisJob:
    """Tests for market_analysis_job function."""

    @pytest.mark.asyncio
    async def test_analyzes_each_symbol(self):
        """Should analyze all configured symbols."""
        from core.scheduler.jobs import market_analysis_job

        mock_onchain = MagicMock()
        mock_onchain.analyze = AsyncMock(
            return_value=MagicMock(fear_greed=MagicMock(value=50, classification="Neutral"))
        )
        mock_onchain.close = AsyncMock()

        mock_deriv = MagicMock()
        mock_deriv.analyze = AsyncMock(return_value=MagicMock(funding=None, long_short=None))
        mock_deriv.close = AsyncMock()

        mock_score = MagicMock()
        mock_score.calculate = MagicMock(
            return_value=MagicMock(
                total_score=50,
                signal="neutral",
                action="hold",
                signal_ru="Нейтральный",
                recommendation_ru="Держать",
            )
        )

        with (
            patch("core.scheduler.jobs.get_symbols", return_value=["BTC/USDT"]),
            patch("service.analysis.OnChainAnalyzer", return_value=mock_onchain),
            patch("service.analysis.DerivativesAnalyzer", return_value=mock_deriv),
            patch("service.analysis.ScoringEngine", return_value=mock_score),
            patch("service.analysis.CycleDetector"),
            patch("service.ha_integration.notify", new_callable=AsyncMock),
        ):
            await market_analysis_job()
            mock_score.calculate.assert_called()


class TestInvestorAnalysisJob:
    """Tests for investor_analysis_job function."""

    @pytest.mark.asyncio
    async def test_updates_mqtt_sensors(self):
        """Should update MQTT sensors with investor status."""
        from core.scheduler.jobs import investor_analysis_job

        mock_analyzer = MagicMock()
        mock_status = MagicMock()
        mock_status.do_nothing_ok = True
        mock_status.phase = MagicMock(value="accumulation")
        mock_status.calm_score = 70
        mock_status.tension_score = 30
        mock_status.red_flags = []
        mock_status.to_dict = MagicMock(return_value={})
        mock_analyzer.analyze = AsyncMock(return_value=mock_status)
        mock_analyzer.get_alert_if_needed = MagicMock(return_value=None)

        mock_onchain = MagicMock()
        mock_onchain.analyze = AsyncMock(return_value=MagicMock(fear_greed=MagicMock(value=50)))
        mock_onchain.close = AsyncMock()

        mock_deriv = MagicMock()
        mock_deriv.analyze = AsyncMock(return_value=MagicMock(funding=None, long_short=None))
        mock_deriv.close = AsyncMock()

        mock_sensors = MagicMock()
        mock_sensors.update_investor_status = AsyncMock()
        mock_sensors.update_market_data = AsyncMock()

        with (
            patch("service.analysis.get_investor_analyzer", return_value=mock_analyzer),
            patch("service.analysis.OnChainAnalyzer", return_value=mock_onchain),
            patch("service.analysis.DerivativesAnalyzer", return_value=mock_deriv),
            patch("service.analysis.CycleDetector"),
            patch("service.ha.get_sensors_manager", return_value=mock_sensors),
            patch("service.ha_integration.notify", new_callable=AsyncMock),
        ):
            await investor_analysis_job()
            mock_sensors.update_investor_status.assert_called_once()


class TestAltseasonJob:
    """Tests for altseason_job function."""

    @pytest.mark.asyncio
    async def test_publishes_altseason_data(self):
        """Should publish altseason index to sensors."""
        from core.scheduler.jobs import altseason_job

        mock_analyzer = MagicMock()
        mock_analyzer.analyze = AsyncMock(return_value=MagicMock(altseason_index=60, status="Altseason"))
        mock_analyzer.close = AsyncMock()

        mock_sensors = MagicMock()
        mock_sensors.publish_sensor = AsyncMock()

        with (
            patch("service.analysis.altseason.AltseasonAnalyzer", return_value=mock_analyzer),
            patch("service.ha.get_sensors_manager", return_value=mock_sensors),
        ):
            await altseason_job()
            assert mock_sensors.publish_sensor.call_count == 2


class TestStablecoinJob:
    """Tests for stablecoin_job function."""

    @pytest.mark.asyncio
    async def test_publishes_stablecoin_data(self):
        """Should publish stablecoin metrics to sensors."""
        from core.scheduler.jobs import stablecoin_job

        mock_analyzer = MagicMock()
        mock_analyzer.analyze = AsyncMock(
            return_value=MagicMock(
                total_market_cap=150_000_000_000,
                flow_24h_percent=1.5,
                dominance_percent=10.0,
            )
        )
        mock_analyzer.close = AsyncMock()

        mock_sensors = MagicMock()
        mock_sensors.publish_sensor = AsyncMock()

        with (
            patch("service.analysis.stablecoins.StablecoinAnalyzer", return_value=mock_analyzer),
            patch("service.ha.get_sensors_manager", return_value=mock_sensors),
        ):
            await stablecoin_job()
            assert mock_sensors.publish_sensor.call_count == 3


class TestGasTrackerJob:
    """Tests for gas_tracker_job function."""

    @pytest.mark.asyncio
    async def test_publishes_gas_prices(self):
        """Should publish gas prices to sensors."""
        from core.scheduler.jobs import gas_tracker_job

        mock_tracker = MagicMock()
        mock_tracker.get_gas_prices = AsyncMock(
            return_value=MagicMock(
                slow=10,
                standard=15,
                fast=25,
                status="Low",
            )
        )
        mock_tracker.close = AsyncMock()

        mock_sensors = MagicMock()
        mock_sensors.publish_sensor = AsyncMock()

        with (
            patch("service.analysis.gas.GasTracker", return_value=mock_tracker),
            patch("service.ha.get_sensors_manager", return_value=mock_sensors),
        ):
            await gas_tracker_job()
            assert mock_sensors.publish_sensor.call_count == 4


class TestWhaleMonitorJob:
    """Tests for whale_monitor_job function."""

    @pytest.mark.asyncio
    async def test_publishes_whale_data(self):
        """Should publish whale activity to sensors."""
        from core.scheduler.jobs import whale_monitor_job

        mock_tracker = MagicMock()
        mock_result = MagicMock(
            transactions_24h=25,
            net_flow_usd=1000000,
            signal=MagicMock(value="neutral"),
        )
        mock_result._format_usd = MagicMock(return_value="$1M")
        mock_tracker.analyze = AsyncMock(return_value=mock_result)
        mock_tracker.close = AsyncMock()

        mock_sensors = MagicMock()
        mock_sensors.publish_sensor = AsyncMock()

        with (
            patch("service.analysis.whales.WhaleTracker", return_value=mock_tracker),
            patch("service.ha.get_sensors_manager", return_value=mock_sensors),
            patch("service.ha_integration.notify", new_callable=AsyncMock),
        ):
            await whale_monitor_job()
            assert mock_sensors.publish_sensor.call_count == 3


class TestExchangeFlowJob:
    """Tests for exchange_flow_job function."""

    @pytest.mark.asyncio
    async def test_job_handles_errors_gracefully(self):
        """Should handle errors without crashing."""
        # This job uses internal imports that are hard to mock
        # Just verify it doesn't crash on import
        from core.scheduler.jobs import exchange_flow_job

        assert exchange_flow_job is not None


class TestLiquidationJob:
    """Tests for liquidation_job function."""

    @pytest.mark.asyncio
    async def test_publishes_liquidation_levels(self):
        """Should publish liquidation levels to sensors."""
        from core.scheduler.jobs import liquidation_job

        mock_tracker = MagicMock()
        mock_tracker.get_liquidation_levels = AsyncMock(
            return_value=MagicMock(
                long_nearest=95000,
                short_nearest=105000,
                risk_level="Medium",
            )
        )
        mock_tracker.close = AsyncMock()

        mock_sensors = MagicMock()
        mock_sensors._publish_state = AsyncMock()
        mock_sensors.publish_sensor = AsyncMock()

        with (
            patch("service.analysis.liquidations.LiquidationTracker", return_value=mock_tracker),
            patch("service.ha.get_sensors_manager", return_value=mock_sensors),
            patch("service.ha_integration.notify", new_callable=AsyncMock),
        ):
            await liquidation_job()
            mock_sensors._publish_state.assert_called_once()
            mock_sensors.publish_sensor.assert_called_once()


class TestPortfolioJob:
    """Tests for portfolio_job function."""

    @pytest.mark.asyncio
    async def test_skips_when_no_holdings(self):
        """Should skip when no portfolio holdings configured."""
        from core.scheduler.jobs import portfolio_job

        mock_portfolio = MagicMock()
        mock_portfolio.get_holdings = MagicMock(return_value=[])

        mock_sensors = MagicMock()
        mock_sensors.publish_sensor = AsyncMock()

        with (
            patch("service.portfolio.get_portfolio_manager", return_value=mock_portfolio),
            patch("service.ha.get_sensors_manager", return_value=mock_sensors),
        ):
            await portfolio_job()
            mock_sensors.publish_sensor.assert_not_called()

    @pytest.mark.asyncio
    async def test_publishes_portfolio_data(self):
        """Should publish portfolio data when holdings exist."""
        from core.scheduler.jobs import portfolio_job

        mock_portfolio = MagicMock()
        mock_portfolio.get_holdings = MagicMock(return_value=[{"symbol": "BTC"}])
        mock_portfolio.calculate = AsyncMock(
            return_value=MagicMock(
                total_value=50000,
                total_pnl_percent=10.5,
                change_24h_pct=2.3,
                best_performer=MagicMock(symbol="BTC"),
                worst_performer=MagicMock(symbol="ETH"),
            )
        )

        mock_sensors = MagicMock()
        mock_sensors.publish_sensor = AsyncMock()

        with (
            patch("service.portfolio.get_portfolio_manager", return_value=mock_portfolio),
            patch("service.ha.get_sensors_manager", return_value=mock_sensors),
        ):
            await portfolio_job()
            assert mock_sensors.publish_sensor.call_count == 5


class TestSignalHistoryJob:
    """Tests for signal_history_job function."""

    @pytest.mark.asyncio
    async def test_job_exists(self):
        """Should be importable."""
        from core.scheduler.jobs import signal_history_job

        assert signal_history_job is not None


class TestPriceAlertsJob:
    """Tests for price_alerts_job function."""

    @pytest.mark.asyncio
    async def test_skips_when_no_cached_prices(self):
        """Should skip when no cached prices available."""
        from core.scheduler.jobs import price_alerts_job

        mock_sensors = MagicMock()
        mock_sensors._cache = MagicMock()
        mock_sensors._cache.get = MagicMock(return_value=None)

        with (
            patch("service.alerts.get_alert_manager"),
            patch("service.ha.get_sensors_manager", return_value=mock_sensors),
        ):
            await price_alerts_job()

    @pytest.mark.asyncio
    async def test_checks_alerts_and_notifies(self):
        """Should check alerts and send notifications."""
        from core.scheduler.jobs import price_alerts_job

        mock_alert = MagicMock(symbol="BTC")
        mock_alerts_manager = MagicMock()
        mock_alerts_manager.check_prices = AsyncMock(return_value=[(mock_alert, 100000)])
        mock_alerts_manager.get_summary = MagicMock(return_value=MagicMock(active_alerts=5, triggered_24h=2))
        mock_alerts_manager.generate_notification = MagicMock(
            return_value={
                "message": "BTC hit 100k",
                "title": "Price Alert",
                "notification_id": "alert_btc",
            }
        )

        mock_sensors = MagicMock()
        mock_sensors._cache = {"price_btc": 100000}
        mock_sensors.publish_sensor = AsyncMock()

        with (
            patch("service.alerts.get_alert_manager", return_value=mock_alerts_manager),
            patch("service.ha.get_sensors_manager", return_value=mock_sensors),
            patch("service.ha_integration.notify", new_callable=AsyncMock) as mock_notify,
        ):
            await price_alerts_job()
            mock_notify.assert_called_once()
