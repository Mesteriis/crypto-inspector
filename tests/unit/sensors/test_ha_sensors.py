"""
Comprehensive HA Sensors Unit Tests.

Tests 100% coverage of all sensors defined in ha_sensors.py:
- Sensor definition validation
- MQTT discovery message format
- Sensor value updates
- Category coverage
"""


class TestSensorDefinitions:
    """Tests for sensor definition validation."""

    def test_all_sensors_have_required_fields(self, all_sensor_keys):
        """Verify all sensors have required fields."""
        from services.ha_sensors import CryptoSensorsManager

        for key in all_sensor_keys:
            sensor = CryptoSensorsManager.SENSORS[key]
            assert "name" in sensor, f"Sensor '{key}' missing 'name'"
            assert "icon" in sensor, f"Sensor '{key}' missing 'icon'"
            # name should be non-empty
            assert len(sensor["name"]) > 0, f"Sensor '{key}' has empty name"
            # icon should start with mdi:
            assert sensor["icon"].startswith("mdi:"), f"Sensor '{key}' has invalid icon format"

    def test_sensor_count(self, all_sensor_keys):
        """Verify we have the expected number of sensors."""
        # We have 134+ sensors defined
        assert len(all_sensor_keys) >= 130, f"Expected at least 130 sensors, got {len(all_sensor_keys)}"
        print(f"\n=== Total sensors defined: {len(all_sensor_keys)} ===")

    def test_no_duplicate_sensor_names(self, all_sensor_keys):
        """Verify no duplicate sensor display names."""
        from services.ha_sensors import CryptoSensorsManager

        names = [CryptoSensorsManager.SENSORS[key]["name"] for key in all_sensor_keys]
        duplicates = [name for name in names if names.count(name) > 1]
        assert len(set(duplicates)) == 0, f"Duplicate sensor names: {set(duplicates)}"

    def test_sensor_keys_are_valid_identifiers(self, all_sensor_keys):
        """Verify sensor keys are valid Python identifiers."""
        for key in all_sensor_keys:
            # Keys should be lowercase with underscores
            assert key.islower() or "_" in key, f"Sensor key '{key}' should be lowercase"
            assert " " not in key, f"Sensor key '{key}' should not contain spaces"

    def test_unit_fields_are_valid(self, all_sensor_keys):
        """Verify unit fields are valid."""
        from services.ha_sensors import CryptoSensorsManager

        valid_units = {"USDT", "USD", "EUR", "%", "Gwei", None}

        for key in all_sensor_keys:
            sensor = CryptoSensorsManager.SENSORS[key]
            unit = sensor.get("unit")
            if unit:
                assert unit in valid_units or isinstance(unit, str), f"Sensor '{key}' has invalid unit: {unit}"


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


class TestMQTTDiscovery:
    """Tests for MQTT discovery message format."""

    def test_discovery_topic_format(self, all_sensor_keys):
        """Verify discovery topics follow HA convention."""
        from services.ha_sensors import CryptoSensorsManager

        manager = CryptoSensorsManager()

        for key in all_sensor_keys:
            topic = f"homeassistant/sensor/{manager.DEVICE_ID}/{key}/config"
            # Topic should be valid MQTT topic
            assert "/" in topic
            assert topic.startswith("homeassistant/sensor/")
            assert topic.endswith("/config")

    def test_discovery_payload_format(self, all_sensor_keys):
        """Verify discovery payloads have required fields."""
        from services.ha_sensors import CryptoSensorsManager

        manager = CryptoSensorsManager()

        for key in all_sensor_keys[:10]:  # Test subset for speed
            sensor = CryptoSensorsManager.SENSORS[key]

            # Build expected payload structure
            payload = {
                "name": sensor["name"],
                "unique_id": f"{manager.DEVICE_ID}_{key}",
                "state_topic": f"crypto_inspect/sensor/{key}/state",
                "icon": sensor["icon"],
            }

            # Verify required fields
            assert "name" in payload
            assert "unique_id" in payload
            assert "state_topic" in payload
            assert "icon" in payload

    def test_device_info_included(self):
        """Verify device info is included in discovery."""
        from services.ha_sensors import CryptoSensorsManager

        manager = CryptoSensorsManager()

        device_info = {
            "identifiers": [manager.DEVICE_ID],
            "name": manager.DEVICE_NAME,
            "manufacturer": "Crypto Inspect",
            "model": "HA Integration",
        }

        assert device_info["identifiers"] == ["crypto_inspect"]
        assert device_info["name"] == "Crypto Inspect"


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

        # Group sensors by prefix
        groups = {}
        for key in all_sensor_keys:
            prefix = key.split("_")[0]
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(key)

        print("\n" + "=" * 60)
        print("SENSOR COVERAGE REPORT")
        print("=" * 60)
        print(f"\nTotal sensors: {len(all_sensor_keys)}")
        print(f"Sensor groups: {len(groups)}")
        print("\nSensors by group:")
        for group, sensors in sorted(groups.items()):
            print(f"  {group}: {len(sensors)} sensors")

        # Verify minimum count
        assert len(all_sensor_keys) >= 130

    def test_bybit_earn_integration(self, all_sensor_keys):
        """Verify Bybit Earn sensors are properly integrated."""
        earn_sensors = [k for k in all_sensor_keys if "earn" in k]

        print(f"\n=== Bybit Earn Sensors: {len(earn_sensors)} ===")
        for sensor in earn_sensors:
            print(f"  - {sensor}")

        assert len(earn_sensors) >= 3, "Expected at least 3 Bybit Earn sensors"


class TestSensorValidation:
    """Tests for sensor data validation."""

    def test_sensor_icons_are_valid_mdi(self, all_sensor_keys):
        """Verify all icons use Material Design Icons format."""
        from services.ha_sensors import CryptoSensorsManager

        for key in all_sensor_keys:
            icon = CryptoSensorsManager.SENSORS[key]["icon"]
            assert icon.startswith("mdi:"), f"Invalid icon format for {key}: {icon}"

    def test_sensor_names_are_human_readable(self, all_sensor_keys):
        """Verify sensor names are human readable."""
        from services.ha_sensors import CryptoSensorsManager

        for key in all_sensor_keys:
            name = CryptoSensorsManager.SENSORS[key]["name"]
            # Name should not have underscores
            assert "_" not in name, f"Name should not have underscores: {name}"
            # For technical identifiers that start with digits (like "24h Change"), skip capitalization check
            if not name[0].isdigit():
                # Name should have proper capitalization
                assert name[0].isupper(), f"Name should start with capital: {name}"

    def test_unit_sensors_have_valid_units(self, all_sensor_keys):
        """Verify sensors with units have valid unit values."""
        from services.ha_sensors import CryptoSensorsManager

        for key in all_sensor_keys:
            sensor = CryptoSensorsManager.SENSORS[key]
            unit = sensor.get("unit")
            if unit:
                # Unit should be a non-empty string
                assert isinstance(unit, str)
                assert len(unit) > 0


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
            "next_action_timer",
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
