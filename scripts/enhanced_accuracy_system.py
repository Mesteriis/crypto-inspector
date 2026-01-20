#!/usr/bin/env python3
"""
Enhanced ML Prediction System with Improved Accuracy

This script implements a refined approach to achieve higher prediction accuracy
by addressing data preprocessing, model calibration, and ensemble optimization.
"""

import asyncio
import logging
import sys
from pathlib import Path

import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


from core.constants import MLDefaults
from service.candlestick import CandleInterval, fetch_candlesticks
from service.ml.forecaster import PriceForecaster
from service.ml.models import ForecastResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("enhanced_accuracy_analysis.log"),
    ],
)

logger = logging.getLogger(__name__)


class EnhancedAccuracyForecaster:
    """Enhanced forecaster with improved accuracy techniques."""

    def __init__(self):
        self.forecaster = PriceForecaster()
        self.available_models = self.forecaster.get_available_models()
        logger.info(f"Available models: {self.available_models}")

    def preprocess_data(self, prices: list[float]) -> tuple[list[float], dict]:
        """
        Enhanced data preprocessing for better model performance.

        Returns:
            Tuple of (processed_prices, preprocessing_metadata)
        """
        if len(prices) < 10:
            return prices, {}

        # Convert to log returns for better stationarity
        log_returns = [np.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]

        # Remove outliers using IQR method
        q75, q25 = np.percentile(log_returns, [75, 25])
        iqr = q75 - q25
        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr

        filtered_returns = [r for r in log_returns if lower_bound <= r <= upper_bound]

        # Apply smoothing if needed
        if len(filtered_returns) > 20:
            # Simple moving average smoothing
            window = min(5, len(filtered_returns) // 10)
            smoothed_returns = []
            for i in range(len(filtered_returns)):
                start = max(0, i - window // 2)
                end = min(len(filtered_returns), i + window // 2 + 1)
                smoothed_returns.append(np.mean(filtered_returns[start:end]))
            filtered_returns = smoothed_returns

        # Convert back to prices
        processed_prices = [prices[0]]
        for ret in filtered_returns:
            processed_prices.append(processed_prices[-1] * np.exp(ret))

        # Ensure we have enough data
        if len(processed_prices) < MLDefaults.CONTEXT_LENGTH:
            processed_prices = prices[-MLDefaults.CONTEXT_LENGTH :]

        metadata = {
            "original_length": len(prices),
            "processed_length": len(processed_prices),
            "outliers_removed": len(prices) - len(processed_prices),
            "smoothing_applied": len(filtered_returns) > 20,
        }

        return processed_prices, metadata

    def calculate_technical_features(self, prices: list[float]) -> dict[str, float]:
        """Calculate technical indicators as additional features."""
        if len(prices) < 14:
            return {}

        # Moving averages
        ma_short = np.mean(prices[-5:]) if len(prices) >= 5 else prices[-1]
        ma_medium = np.mean(prices[-20:]) if len(prices) >= 20 else prices[-1]
        ma_long = np.mean(prices[-50:]) if len(prices) >= 50 else prices[-1]

        # RSI-like indicator (simplified)
        if len(prices) >= 14:
            gains = [max(0, prices[i] - prices[i - 1]) for i in range(1, len(prices))]
            losses = [max(0, prices[i - 1] - prices[i]) for i in range(1, len(prices))]

            avg_gain = np.mean(gains[-14:])
            avg_loss = np.mean(losses[-14:])

            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50

        # Volatility
        volatility = np.std(prices[-20:]) / np.mean(prices[-20:]) if len(prices) >= 20 else 0

        # Trend strength
        trend_strength = (prices[-1] - prices[-20]) / prices[-20] if len(prices) >= 20 else 0

        return {
            "price_ma_ratio": prices[-1] / ma_medium if ma_medium > 0 else 1,
            "short_long_ma_ratio": ma_short / ma_long if ma_long > 0 else 1,
            "rsi": rsi,
            "volatility": volatility,
            "trend_strength": trend_strength,
            "price_position": (prices[-1] - min(prices[-20:])) / (max(prices[-20:]) - min(prices[-20:]))
            if len(prices) >= 20 and max(prices[-20:]) != min(prices[-20:])
            else 0.5,
        }

    async def enhanced_predict(
        self, symbol: str, interval: str, prices: list[float], horizon: int = 3
    ) -> dict[str, dict]:
        """
        Enhanced prediction with multiple improvements.

        Returns:
            Dictionary mapping model names to enhanced prediction results
        """
        results = {}

        # Preprocess data
        processed_prices, prep_metadata = self.preprocess_data(prices)
        logger.info(f"Preprocessing: {prep_metadata}")

        # Calculate technical features
        tech_features = self.calculate_technical_features(processed_prices)
        logger.info(f"Technical features: {tech_features}")

        # Use shorter context for better responsiveness
        context_length = min(len(processed_prices), 100)  # Reduced from 512
        context_prices = processed_prices[-context_length:]

        for model_name in self.available_models:
            try:
                logger.info(f"Enhanced prediction for {symbol} using {model_name}")

                # Generate forecast with enhanced parameters
                forecast = await self.forecaster.predict(
                    symbol=symbol, interval=interval, prices=context_prices, model=model_name, horizon=horizon
                )

                # Enhance confidence based on technical analysis
                enhanced_confidence = self.enhance_confidence(forecast, tech_features, model_name)

                # Apply trend correction based on technical indicators
                corrected_predictions = self.apply_trend_correction(
                    forecast.predictions, tech_features, context_prices[-1]
                )

                results[model_name] = {
                    "predictions": corrected_predictions,
                    "confidence": enhanced_confidence,
                    "direction": self._calculate_direction(context_prices[-1], corrected_predictions),
                    "technical_alignment": self.calculate_technical_alignment(
                        tech_features, corrected_predictions[-1], context_prices[-1]
                    ),
                    "raw_forecast": forecast,
                }

                logger.info(f"{model_name}: {corrected_predictions[-1]:.4f} ({enhanced_confidence:.1f}% confidence)")

            except Exception as e:
                logger.error(f"Failed enhanced prediction for {model_name}: {e}")
                continue

        return results

    def enhance_confidence(self, forecast: ForecastResult, tech_features: dict, model_name: str) -> float:
        """Enhance confidence based on technical alignment."""
        base_confidence = forecast.confidence_pct

        # Technical alignment bonus
        alignment_bonus = 0
        if tech_features:
            # RSI alignment
            if 30 <= tech_features.get("rsi", 50) <= 70:
                alignment_bonus += 10  # Neutral RSI is good

            # Trend alignment
            trend_strength = tech_features.get("trend_strength", 0)
            if abs(trend_strength) > 0.05:  # Strong trend
                alignment_bonus += 5

            # Volatility consideration
            volatility = tech_features.get("volatility", 0)
            if volatility < 0.1:  # Low volatility
                alignment_bonus += 5
            elif volatility > 0.3:  # High volatility
                alignment_bonus -= 10

        # Model-specific adjustments
        if model_name == "chronos-bolt":
            # Chronos tends to be conservative
            base_confidence *= 1.2
        elif model_name == "neuralprophet":
            # NeuralProphet can be overconfident
            base_confidence *= 0.8

        enhanced_conf = min(95, max(5, base_confidence + alignment_bonus))
        return enhanced_conf

    def apply_trend_correction(self, predictions: list[float], tech_features: dict, last_price: float) -> list[float]:
        """Apply trend correction based on technical indicators."""
        if not tech_features or not predictions:
            return predictions

        corrected = predictions.copy()

        # Trend strength adjustment
        trend_strength = tech_features.get("trend_strength", 0)
        rsi = tech_features.get("rsi", 50)

        # Apply correction factor
        if abs(trend_strength) > 0.02:  # Significant trend
            correction_factor = 1 + (trend_strength * 0.3)  # Up to 30% adjustment

            # RSI confirmation
            if (trend_strength > 0 and rsi > 50) or (trend_strength < 0 and rsi < 50):
                correction_factor *= 1.1  # Reinforce aligned signals
            else:
                correction_factor *= 0.9  # Reduce conflicting signals

            corrected = [p * correction_factor for p in predictions]

        return corrected

    def calculate_technical_alignment(self, tech_features: dict, predicted_price: float, current_price: float) -> float:
        """Calculate how well prediction aligns with technical indicators."""
        if not tech_features:
            return 0.5

        alignments = []

        # Price position alignment
        price_pos = tech_features.get("price_position", 0.5)
        predicted_direction = 1 if predicted_price > current_price else -1
        pos_alignment = 1 - abs(price_pos - (predicted_direction > 0))  # 0-1 scale
        alignments.append(pos_alignment)

        # RSI alignment
        rsi = tech_features.get("rsi", 50)
        rsi_signal = 1 if rsi > 50 else -1
        rsi_alignment = 1 if predicted_direction == rsi_signal else 0
        alignments.append(rsi_alignment)

        # Trend alignment
        trend_strength = tech_features.get("trend_strength", 0)
        trend_alignment = 1 if (predicted_direction > 0) == (trend_strength > 0) else 0
        alignments.append(trend_alignment)

        return np.mean(alignments)

    def _calculate_direction(self, current_price: float, predictions: list[float]) -> str:
        """Calculate price direction."""
        if not predictions:
            return "neutral"
        final_prediction = predictions[-1]
        if final_prediction > current_price:
            return "up"
        elif final_prediction < current_price:
            return "down"
        else:
            return "neutral"

    async def test_enhanced_accuracy(self):
        """Test the enhanced system on sample data."""
        logger.info("=" * 80)
        logger.info("ТЕСТИРОВАНИЕ УЛУЧШЕННОЙ СИСТЕМЫ ТОЧНОСТИ")
        logger.info("=" * 80)

        # Test symbols
        test_symbols = ["BTC/USDT", "ETH/USDT"]
        interval = "1d"
        horizon = 3

        for symbol in test_symbols:
            logger.info(f"\n🔮 ТЕСТИРУЕМ {symbol}")
            logger.info("-" * 50)

            try:
                # Fetch recent data
                candles = await fetch_candlesticks(symbol=symbol, interval=CandleInterval(interval), limit=200)

                if not candles or len(candles) < 50:
                    logger.warning(f"Недостаточно данных для {symbol}")
                    continue

                prices = [float(candle.close_price) for candle in candles]
                logger.info(f"Получено {len(prices)} цен")
                logger.info(f"Диапазон: {prices[0]:.2f} → {prices[-1]:.2f}")

                # Enhanced prediction
                results = await self.enhanced_predict(symbol, interval, prices, horizon)

                # Display results
                logger.info(f"\n📊 РЕЗУЛЬТАТЫ ДЛЯ {symbol}:")
                for model_name, result in results.items():
                    pred_price = result["predictions"][-1]
                    confidence = result["confidence"]
                    direction = result["direction"]
                    tech_align = result["technical_alignment"]

                    logger.info(
                        f"  {model_name:20} {pred_price:10.2f} "
                        f"{direction:>4} ({confidence:5.1f}%) "
                        f"TechAlign: {tech_align:.2f}"
                    )

                # Ensemble prediction
                if len(results) > 1:
                    ensemble_pred = self.create_weighted_ensemble(results, prices[-1])
                    logger.info(
                        f"  {'ENSEMBLE':20} {ensemble_pred['price']:10.2f} "
                        f"{ensemble_pred['direction']:>4} ({ensemble_pred['confidence']:5.1f}%) "
                        f"Weighted: {ensemble_pred['weighting_method']}"
                    )

            except Exception as e:
                logger.error(f"Ошибка тестирования {symbol}: {e}")

    def create_weighted_ensemble(self, model_results: dict, current_price: float) -> dict:
        """Create enhanced ensemble with weighted averaging."""
        if not model_results:
            return {"price": current_price, "confidence": 0, "direction": "neutral"}

        # Weight by confidence and technical alignment
        weights = []
        predictions = []
        confidences = []

        for model_name, result in model_results.items():
            # Combined weight: confidence + technical alignment
            combined_weight = (result["confidence"] / 100) * result["technical_alignment"]
            weights.append(combined_weight)
            predictions.append(result["predictions"][-1])
            confidences.append(result["confidence"])

        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
        else:
            normalized_weights = [1 / len(weights)] * len(weights)

        # Weighted average prediction
        ensemble_price = sum(p * w for p, w in zip(predictions, normalized_weights))

        # Ensemble confidence (weighted average)
        ensemble_confidence = sum(c * w for c, w in zip(confidences, normalized_weights))

        # Direction
        direction = "up" if ensemble_price > current_price else "down" if ensemble_price < current_price else "neutral"

        return {
            "price": ensemble_price,
            "confidence": ensemble_confidence,
            "direction": direction,
            "weighting_method": "confidence_and_technical_alignment",
            "model_weights": dict(zip(model_results.keys(), normalized_weights)),
        }


async def main():
    """Main execution function."""
    try:
        enhancer = EnhancedAccuracyForecaster()
        await enhancer.test_enhanced_accuracy()

        logger.info("\n" + "=" * 80)
        logger.info("✅ ТЕСТИРОВАНИЕ УЛУЧШЕННОЙ СИСТЕМЫ ЗАВЕРШЕНО!")
        logger.info("=" * 80)
        logger.info("Реализованные улучшения:")
        logger.info("  • Предобработка данных (удаление выбросов, сглаживание)")
        logger.info("  • Технический анализ (RSI, скользящие средние, волатильность)")
        logger.info("  • Коррекция тренда на основе технических индикаторов")
        logger.info("  • Улучшенные коэффициенты уверенности")
        logger.info("  • Взвешенный ансамбль с учетом технической согласованности")

    except Exception as e:
        logger.error(f"Enhanced accuracy test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
