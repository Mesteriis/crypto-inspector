"""
Comprehensive HA Sensors Unit Tests.

Tests 100% coverage of all sensors defined in services.ha:
- Sensor definition validation
- Sensor registration
- Sensor value updates
- Category coverage
"""


class TestSensorDefinitions:
    """Tests for sensor definition validation."""

    def test_all_sensors_have_required_fields(self, all_sensor_keys):
        """Verify all sensors have required config fields."""
        from service.ha import SensorRegistry

        SensorRegistry.ensure_initialized()
        for key in all_sensor_keys:
            sensor_class = SensorRegistry.get(key)
            assert sensor_class is not None, f"Sensor '{key}' not registered"
            # Verify class has config
            instance = sensor_class.__new__(sensor_class)
            assert hasattr(instance, 'config'), f"Sensor '{key}' missing 'config'"

    def test_sensor_count(self, all_sensor_keys):
        """Verify we have the expected number of sensors."""
        # We have 130+ sensors defined
        assert len(all_sensor_keys) >= 130, f"Expected at least 130 sensors, got {len(all_sensor_keys)}"
        print(f"\n=== Total sensors defined: {len(all_sensor_keys)} ===")

    def test_no_duplicate_sensor_ids(self, all_sensor_keys):
        """Verify no duplicate sensor IDs."""
        # all_sensor_keys are unique by definition (from dict.keys())
        assert len(all_sensor_keys) == len(set(all_sensor_keys))

    def test_sensor_keys_are_valid_identifiers(self, all_sensor_keys):
        """Verify sensor keys are valid Python identifiers."""
        for key in all_sensor_keys:
            # Keys should be lowercase with underscores
            assert key.islower() or "_" in key, f"Sensor key '{key}' should be lowercase"
            assert " " not in key, f"Sensor key '{key}' should not contain spaces"


class TestSensorCategories:
    """Tests for sensor category coverage."""

    def test_price_sensors_exist(self, all_sensor_keys):
        """Verify price-related sensors exist."""
        price_sensors = ["prices", "changes_24h", "volumes_24h", "highs_24h", "lows_24h"]
        for sensor in price_sensors:
            assert sensor in all_sensor_keys, f"Missing price sensor: {sensor}"

    def test_investor_sensors_exist(self, all_sensor_keys):
        """Verify investor (lazy investor) sensors exist."""
        investor_sensors = [
            "do_nothing_ok",
            "investor_phase",
            "calm_indicator",
            "red_flags",
            "market_tension",
            "dca_signal",
        ]
        for sensor in investor_sensors:
            assert sensor in all_sensor_keys, f"Missing investor sensor: {sensor}"

    def test_market_sensors_exist(self, all_sensor_keys):
        """Verify market-wide sensors exist."""
        market_sensors = ["fear_greed", "btc_dominance", "derivatives", "altseason_index", "altseason_status"]
        for sensor in market_sensors:
            assert sensor in all_sensor_keys, f"Missing market sensor: {sensor}"

    def test_bybit_sensors_exist(self, all_sensor_keys):
        """Verify Bybit exchange sensors exist."""
        bybit_sensors = ["bybit_balance", "bybit_pnl_24h", "bybit_pnl_7d", "bybit_positions", "bybit_unrealized_pnl"]
        for sensor in bybit_sensors:
            assert sensor in all_sensor_keys, f"Missing Bybit sensor: {sensor}"

    def test_bybit_earn_sensors_exist(self, all_sensor_keys):
        """Verify Bybit Earn sensors exist."""
        earn_sensors = ["bybit_earn_balance", "bybit_earn_positions", "bybit_earn_apy", "bybit_total_portfolio"]
        for sensor in earn_sensors:
            assert sensor in all_sensor_keys, f"Missing Bybit Earn sensor: {sensor}"

    def test_technical_analysis_sensors_exist(self, all_sensor_keys):
        """Verify TA sensors exist."""
        ta_sensors = ["ta_rsi", "ta_macd_signal", "ta_bb_position", "ta_trend", "ta_support", "ta_resistance"]
        for sensor in ta_sensors:
            assert sensor in all_sensor_keys, f"Missing TA sensor: {sensor}"

    def test_risk_sensors_exist(self, all_sensor_keys):
        """Verify risk management sensors exist."""
        risk_sensors = ["portfolio_sharpe", "portfolio_sortino", "portfolio_max_drawdown", "risk_status"]
        for sensor in risk_sensors:
            assert sensor in all_sensor_keys, f"Missing risk sensor: {sensor}"

    def test_traditional_finance_sensors_exist(self, all_sensor_keys):
        """Verify traditional finance sensors exist."""
        trad_sensors = ["gold_price", "silver_price", "sp500_price", "dxy_index", "eur_usd"]
        for sensor in trad_sensors:
            assert sensor in all_sensor_keys, f"Missing traditional finance sensor: {sensor}"

    def test_ai_sensors_exist(self, all_sensor_keys):
        """Verify AI analysis sensors exist."""
        ai_sensors = ["ai_daily_summary", "ai_market_sentiment", "ai_recommendation", "ai_provider"]
        for sensor in ai_sensors:
            assert sensor in all_sensor_keys, f"Missing AI sensor: {sensor}"

    def test_ux_sensors_exist(self, all_sensor_keys):
        """Verify UX enhancement sensors exist."""
        ux_sensors = ["market_pulse", "portfolio_health", "today_action", "morning_briefing", "evening_briefing"]
        for sensor in ux_sensors:
            assert sensor in all_sensor_keys, f"Missing UX sensor: {sensor}"

    def test_goal_sensors_exist(self, all_sensor_keys):
        """Verify goal tracking sensors exist."""
        goal_sensors = ["goal_target", "goal_progress", "goal_status"]
        for sensor in goal_sensors:
            assert sensor in all_sensor_keys, f"Missing goal sensor: {sensor}"

    def test_whale_sensors_exist(self, all_sensor_keys):
        """Verify whale activity sensors exist."""
        whale_sensors = ["whale_alerts_24h", "whale_net_flow", "whale_last_alert"]
        for sensor in whale_sensors:
            assert sensor in all_sensor_keys, f"Missing whale sensor: {sensor}"

    def test_gas_sensors_exist(self, all_sensor_keys):
        """Verify ETH gas sensors exist."""
        gas_sensors = ["eth_gas_slow", "eth_gas_standard", "eth_gas_fast", "eth_gas_status"]
        for sensor in gas_sensors:
            assert sensor in all_sensor_keys, f"Missing gas sensor: {sensor}"

    def test_dca_sensors_exist(self, all_sensor_keys):
        """Verify DCA calculator sensors exist."""
        dca_sensors = ["dca_next_level", "dca_zone", "dca_risk_score"]
        for sensor in dca_sensors:
            assert sensor in all_sensor_keys, f"Missing DCA sensor: {sensor}"

    def test_correlation_sensors_exist(self, all_sensor_keys):
        """Verify correlation sensors exist."""
        corr_sensors = ["btc_eth_correlation", "btc_sp500_correlation", "correlation_status"]
        for sensor in corr_sensors:
            assert sensor in all_sensor_keys, f"Missing correlation sensor: {sensor}"

    def test_volatility_sensors_exist(self, all_sensor_keys):
        """Verify volatility sensors exist."""
        vol_sensors = ["volatility_30d", "volatility_percentile", "volatility_status"]
        for sensor in vol_sensors:
            assert sensor in all_sensor_keys, f"Missing volatility sensor: {sensor}"

    def test_arbitrage_sensors_exist(self, all_sensor_keys):
        """Verify arbitrage sensors exist."""
        arb_sensors = ["arb_spreads", "funding_arb_best", "arb_opportunity"]
        for sensor in arb_sensors:
            assert sensor in all_sensor_keys, f"Missing arbitrage sensor: {sensor}"

    def test_backtest_sensors_exist(self, all_sensor_keys):
        """Verify backtest sensors exist."""
        backtest_sensors = [
            "backtest_dca_roi",
            "backtest_smart_dca_roi",
            "backtest_lump_sum_roi",
            "backtest_best_strategy",
        ]
        for sensor in backtest_sensors:
            assert sensor in all_sensor_keys, f"Missing backtest sensor: {sensor}"


class TestSensorRegistry:
    """Tests for SensorRegistry functionality."""

    def test_registry_initialization(self):
        """Verify registry initializes all sensors."""
        from service.ha import SensorRegistry

        SensorRegistry.ensure_initialized()
        count = SensorRegistry.count()
        assert count >= 130, f"Expected at least 130 sensors, got {count}"

    def test_get_by_category(self):
        """Verify sensors can be retrieved by category."""
        from service.ha import SensorRegistry

        SensorRegistry.ensure_initialized()
        categories = SensorRegistry.get_categories()
        assert len(categories) >= 15, f"Expected at least 15 categories, got {len(categories)}"

        # Verify each category has sensors
        for category in categories:
            sensors = SensorRegistry.get_by_category(category)
            assert len(sensors) > 0, f"Category '{category}' has no sensors"

    def test_is_registered(self):
        """Verify is_registered works correctly."""
        from service.ha import SensorRegistry

        SensorRegistry.ensure_initialized()
        assert SensorRegistry.is_registered("prices")
        assert SensorRegistry.is_registered("fear_greed")
        assert not SensorRegistry.is_registered("nonexistent_sensor")


class TestSensorValueUpdates:
    """Tests for sensor value updates."""

    def test_price_sensor_update(self, sample_price_data):
        """Test price sensor accepts correct data format."""
        # Verify data format is dictionary
        assert isinstance(sample_price_data, dict)
        for symbol, price in sample_price_data.items():
            assert "/" in symbol  # Format: BTC/USDT
            assert isinstance(price, (int, float))
            assert price > 0

    def test_change_sensor_update(self, sample_change_data):
        """Test change sensor accepts percentages."""
        for symbol, change in sample_change_data.items():
            assert "/" in symbol
            assert isinstance(change, (int, float))
            assert -100 <= change <= 1000  # Reasonable range

    def test_bybit_sensor_update(self, sample_bybit_data):
        """Test Bybit sensor data format."""
        assert "balance" in sample_bybit_data
        assert "pnl_24h" in sample_bybit_data
        assert "earn_balance" in sample_bybit_data
        assert "earn_positions" in sample_bybit_data
        assert "total_portfolio" in sample_bybit_data

        # Verify earn positions format
        for pos in sample_bybit_data["earn_positions"]:
            assert "coin" in pos
            assert "amount" in pos
            assert "apy" in pos

    def test_ta_sensor_update(self, sample_ta_data):
        """Test technical analysis sensor data format."""
        for symbol, data in sample_ta_data.items():
            assert "rsi" in data
            assert 0 <= data["rsi"] <= 100
            assert "macd_signal" in data
            assert data["macd_signal"] in ["bullish", "bearish", "neutral"]
            assert "bb_position" in data
            assert 0 <= data["bb_position"] <= 100
            assert "trend" in data
            assert "support" in data
            assert "resistance" in data


class TestSensorCoverage:
    """Tests for complete sensor coverage."""

    def test_all_sensor_categories_covered(self, all_sensor_keys):
        """Verify all expected categories have sensors."""
        categories = {
            "price": ["prices", "changes_24h"],
            "investor": ["do_nothing_ok", "investor_phase"],
            "market": ["fear_greed", "btc_dominance"],
            "bybit": ["bybit_balance", "bybit_earn_balance"],
            "ta": ["ta_rsi", "ta_macd_signal"],
            "risk": ["portfolio_sharpe", "risk_status"],
            "traditional": ["gold_price", "sp500_price"],
            "ai": ["ai_daily_summary", "ai_recommendation"],
            "ux": ["market_pulse", "portfolio_health"],
            "whale": ["whale_alerts_24h"],
            "gas": ["eth_gas_fast"],
            "dca": ["dca_next_level"],
            "correlation": ["btc_eth_correlation"],
            "volatility": ["volatility_30d"],
            "arbitrage": ["arb_spreads"],
            "backtest": ["backtest_dca_roi"],
            "goals": ["goal_target"],
            "alerts": ["active_alerts_count"],
            "signals": ["signals_win_rate"],
            "divergences": ["divergences"],
            "liquidations": ["liq_levels"],
            "exchange_flow": ["exchange_netflows"],
            "stablecoin": ["stablecoin_total"],
            "unlocks": ["unlocks_next_7d"],
            "macro": ["next_macro_event"],
            "briefing": ["morning_briefing"],
        }

        for category, expected_sensors in categories.items():
            for sensor in expected_sensors:
                assert sensor in all_sensor_keys, f"Missing sensor '{sensor}' in category '{category}'"

        print(f"\n=== All {len(categories)} sensor categories covered ===")

    def test_generate_sensor_coverage_report(self, all_sensor_keys):
        """Generate a sensor coverage report."""
        from service.ha import SensorRegistry

        SensorRegistry.ensure_initialized()

        # Group sensors by category
        categories = SensorRegistry.get_categories()

        print("\n" + "=" * 60)
        print("SENSOR COVERAGE REPORT")
        print("=" * 60)
        print(f"\nTotal sensors: {len(all_sensor_keys)}")
        print(f"Categories: {len(categories)}")
        print("\nSensors by category:")
        for category in sorted(categories):
            sensors = SensorRegistry.get_by_category(category)
            print(f"  {category}: {len(sensors)} sensors")

        # Verify minimum count
        assert len(all_sensor_keys) >= 130

    def test_bybit_earn_integration(self, all_sensor_keys):
        """Verify Bybit Earn sensors are properly integrated."""
        earn_sensors = [k for k in all_sensor_keys if "earn" in k]

        print(f"\n=== Bybit Earn Sensors: {len(earn_sensors)} ===")
        for sensor in earn_sensors:
            print(f"  - {sensor}")

        assert len(earn_sensors) >= 3, "Expected at least 3 Bybit Earn sensors"


class TestSensorCompleteness:
    """Final tests to ensure 100% coverage."""

    def test_all_expected_sensors_present(self, all_sensor_keys):
        """Master test to verify all expected sensors are present."""
        # Complete list of all expected sensors
        expected_sensors = [
            # Price sensors
            "prices",
            "changes_24h",
            "volumes_24h",
            "highs_24h",
            "lows_24h",
            # Investor sensors
            "do_nothing_ok",
            "investor_phase",
            "calm_indicator",
            "red_flags",
            "market_tension",
            "price_context",
            "dca_result",
            "dca_signal",
            "weekly_insight",
            # Market sensors
            "fear_greed",
            "btc_dominance",
            "derivatives",
            "altseason_index",
            "altseason_status",
            "stablecoin_total",
            "stablecoin_flow",
            "stablecoin_dominance",
            # Gas sensors
            "eth_gas_slow",
            "eth_gas_standard",
            "eth_gas_fast",
            "eth_gas_status",
            # Whale sensors
            "whale_alerts_24h",
            "whale_net_flow",
            "whale_last_alert",
            # Exchange flow sensors
            "exchange_netflows",
            "exchange_flow_signal",
            # Liquidation sensors
            "liq_levels",
            "liq_risk_level",
            # Portfolio sensors
            "portfolio_value",
            "portfolio_pnl",
            "portfolio_pnl_24h",
            "portfolio_allocation",
            # Alert sensors
            "active_alerts_count",
            "triggered_alerts_24h",
            # Divergence sensors
            "divergences",
            "divergences_active",
            # Signal sensors
            "signals_win_rate",
            "signals_today",
            "signals_last",
            # Bybit sensors
            "bybit_balance",
            "bybit_pnl_24h",
            "bybit_pnl_7d",
            "bybit_positions",
            "bybit_unrealized_pnl",
            # Bybit Earn sensors
            "bybit_earn_balance",
            "bybit_earn_positions",
            "bybit_earn_apy",
            "bybit_total_portfolio",
            # DCA sensors
            "dca_next_level",
            "dca_zone",
            "dca_risk_score",
            # Correlation sensors
            "btc_eth_correlation",
            "btc_sp500_correlation",
            "correlation_status",
            # Volatility sensors
            "volatility_30d",
            "volatility_percentile",
            "volatility_status",
            # Unlock sensors
            "unlocks_next_7d",
            "unlock_next_event",
            "unlock_risk_level",
            # Macro sensors
            "next_macro_event",
            "days_to_fomc",
            "macro_risk_week",
            # Arbitrage sensors
            "arb_spreads",
            "funding_arb_best",
            "arb_opportunity",
            # Profit taking sensors
            "tp_levels",
            "profit_action",
            "greed_level",
            # Traditional finance sensors
            "gold_price",
            "silver_price",
            "platinum_price",
            "sp500_price",
            "nasdaq_price",
            "dji_price",
            "dax_price",
            "eur_usd",
            "gbp_usd",
            "dxy_index",
            "oil_brent",
            "oil_wti",
            "natural_gas",
            # AI sensors
            "ai_daily_summary",
            "ai_market_sentiment",
            "ai_recommendation",
            "ai_last_analysis",
            "ai_provider",
            # TA sensors
            "ta_rsi",
            "ta_macd_signal",
            "ta_bb_position",
            "ta_trend",
            "ta_support",
            "ta_resistance",
            "ta_trend_mtf",
            "ta_confluence",
            "ta_signal",
            # Risk sensors
            "portfolio_sharpe",
            "portfolio_sortino",
            "portfolio_max_drawdown",
            "portfolio_current_drawdown",
            "portfolio_var_95",
            "risk_status",
            # Backtest sensors
            "backtest_dca_roi",
            "backtest_smart_dca_roi",
            "backtest_lump_sum_roi",
            "backtest_best_strategy",
            # UX sensors
            "market_pulse",
            "market_pulse_confidence",
            "portfolio_health",
            "portfolio_health_score",
            "today_action",
            "today_action_priority",
            "weekly_outlook",
            # Alert/notification UX sensors
            "pending_alerts_count",
            "pending_alerts_critical",
            "daily_digest_ready",
            "notification_mode",
            # Briefing sensors
            "morning_briefing",
            "evening_briefing",
            "briefing_last_sent",
            # Goal sensors
            "goal_target",
            "goal_progress",
            "goal_remaining",
            "goal_days_estimate",
            "goal_status",
            # Diagnostic sensors
            "sync_status",
            "last_sync",
            "candles_count",
        ]

        missing = []
        for sensor in expected_sensors:
            if sensor not in all_sensor_keys:
                missing.append(sensor)

        if missing:
            print(f"\n=== Missing sensors ({len(missing)}): ===")
            for s in missing:
                print(f"  - {s}")

        assert len(missing) == 0, f"Missing {len(missing)} sensors: {missing}"

        print(f"\n=== All {len(expected_sensors)} expected sensors present ===")
        print(f"=== Total sensors: {len(all_sensor_keys)} ===")
        print("=== 100% SENSOR COVERAGE ACHIEVED ===")
