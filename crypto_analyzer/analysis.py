"""
Technical Analysis Module - Расчёт индикаторов

Индикаторы:
- SMA (Simple Moving Average) - 20, 50, 200
- EMA (Exponential Moving Average) - 12, 26
- RSI (Relative Strength Index) - 14
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- ATR (Average True Range)
- Support/Resistance levels
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


@dataclass
class TechnicalIndicators:
    """Структура для хранения технических индикаторов"""

    symbol: str
    timeframe: str
    timestamp: int
    price: float

    # Moving Averages
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None

    # RSI
    rsi: float | None = None

    # MACD
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None

    # Bollinger Bands
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_position: float | None = None  # 0-100 (нижняя-верхняя)

    # ATR
    atr: float | None = None

    # Volume
    volume_sma: float | None = None
    volume_ratio: float | None = None  # текущий / SMA

    # Дополнительные
    price_change_24h: float | None = None
    price_change_7d: float | None = None

    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "price": self.price,
            "sma_20": self.sma_20,
            "sma_50": self.sma_50,
            "sma_200": self.sma_200,
            "ema_12": self.ema_12,
            "ema_26": self.ema_26,
            "rsi": self.rsi,
            "macd_line": self.macd_line,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "bb_upper": self.bb_upper,
            "bb_middle": self.bb_middle,
            "bb_lower": self.bb_lower,
            "bb_position": self.bb_position,
            "atr": self.atr,
            "volume_sma": self.volume_sma,
            "volume_ratio": self.volume_ratio,
            "price_change_24h": self.price_change_24h,
            "price_change_7d": self.price_change_7d,
        }


class TechnicalAnalyzer:
    """Класс для расчёта технических индикаторов"""

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()

    # ========================================================================
    # БАЗОВЫЕ РАСЧЁТЫ
    # ========================================================================

    @staticmethod
    def calc_sma(prices: list[float], period: int) -> float | None:
        """
        Simple Moving Average

        Args:
            prices: Список цен (от старых к новым)
            period: Период SMA

        Returns:
            Значение SMA или None если недостаточно данных
        """
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    @staticmethod
    def calc_ema(prices: list[float], period: int) -> float | None:
        """
        Exponential Moving Average

        Args:
            prices: Список цен
            period: Период EMA

        Returns:
            Значение EMA
        """
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = prices[0]  # Начинаем с первой цены

        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    @staticmethod
    def calc_ema_series(prices: list[float], period: int) -> list[float]:
        """
        Рассчитать серию EMA значений

        Args:
            prices: Список цен
            period: Период EMA

        Returns:
            Список EMA значений
        """
        if len(prices) < period:
            return []

        multiplier = 2 / (period + 1)
        ema_series = [sum(prices[:period]) / period]  # Первое значение = SMA

        for price in prices[period:]:
            ema = (price * multiplier) + (ema_series[-1] * (1 - multiplier))
            ema_series.append(ema)

        return ema_series

    @staticmethod
    def calc_rsi(prices: list[float], period: int = 14) -> float | None:
        """
        Relative Strength Index

        Args:
            prices: Список цен закрытия
            period: Период RSI (обычно 14)

        Returns:
            RSI значение 0-100
        """
        if len(prices) < period + 1:
            return None

        # Рассчитываем изменения
        changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

        # Разделяем на gains и losses
        gains = [max(0, c) for c in changes]
        losses = [abs(min(0, c)) for c in changes]

        # Первые средние
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Smoothed averages для остальных периодов
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    @staticmethod
    def calc_macd(
        prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple[float | None, float | None, float | None]:
        """
        MACD (Moving Average Convergence Divergence)

        Args:
            prices: Список цен
            fast: Быстрый EMA период
            slow: Медленный EMA период
            signal: Сигнальная линия период

        Returns:
            Tuple (MACD line, Signal line, Histogram)
        """
        if len(prices) < slow + signal:
            return None, None, None

        # Рассчитываем EMA серии
        ema_fast = TechnicalAnalyzer.calc_ema_series(prices, fast)
        ema_slow = TechnicalAnalyzer.calc_ema_series(prices, slow)

        if not ema_fast or not ema_slow:
            return None, None, None

        # MACD line = Fast EMA - Slow EMA
        # Выравниваем серии
        offset = slow - fast
        macd_line_series = [ema_fast[i + offset] - ema_slow[i] for i in range(len(ema_slow))]

        # Signal line = EMA(MACD line)
        if len(macd_line_series) < signal:
            return macd_line_series[-1] if macd_line_series else None, None, None

        signal_line = TechnicalAnalyzer.calc_ema(macd_line_series, signal)
        macd_line = macd_line_series[-1]
        histogram = macd_line - signal_line if signal_line else None

        return (
            round(macd_line, 4) if macd_line else None,
            round(signal_line, 4) if signal_line else None,
            round(histogram, 4) if histogram else None,
        )

    @staticmethod
    def calc_bollinger_bands(
        prices: list[float], period: int = 20, std_dev: float = 2.0
    ) -> tuple[float | None, float | None, float | None, float | None]:
        """
        Bollinger Bands

        Args:
            prices: Список цен
            period: Период SMA
            std_dev: Множитель стандартного отклонения

        Returns:
            Tuple (upper, middle, lower, position 0-100)
        """
        if len(prices) < period:
            return None, None, None, None

        recent_prices = prices[-period:]
        middle = sum(recent_prices) / period

        # Стандартное отклонение
        variance = sum((p - middle) ** 2 for p in recent_prices) / period
        std = variance**0.5

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        # Позиция текущей цены в bands (0-100)
        current_price = prices[-1]
        if upper != lower:
            position = ((current_price - lower) / (upper - lower)) * 100
            position = max(0, min(100, position))
        else:
            position = 50

        return (round(upper, 2), round(middle, 2), round(lower, 2), round(position, 1))

    @staticmethod
    def calc_atr(candles: list[dict], period: int = 14) -> float | None:
        """
        Average True Range

        Args:
            candles: Список свечей с high, low, close
            period: Период ATR

        Returns:
            ATR значение
        """
        if len(candles) < period + 1:
            return None

        true_ranges = []

        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

        # ATR = SMA of True Range
        if len(true_ranges) < period:
            return None

        return round(sum(true_ranges[-period:]) / period, 2)

    # ========================================================================
    # SUPPORT / RESISTANCE
    # ========================================================================

    @staticmethod
    def find_support_resistance(
        candles: list[dict], lookback: int = 50, threshold_pct: float = 0.02
    ) -> dict:
        """
        Найти уровни поддержки и сопротивления

        Args:
            candles: Список свечей
            lookback: Период для поиска
            threshold_pct: Порог кластеризации (2%)

        Returns:
            Dict с уровнями и их силой
        """
        if len(candles) < lookback:
            lookback = len(candles)

        recent_candles = candles[-lookback:]

        # Находим локальные максимумы и минимумы
        highs = []
        lows = []

        for i in range(2, len(recent_candles) - 2):
            # Локальный максимум
            if (
                recent_candles[i]["high"] > recent_candles[i - 1]["high"]
                and recent_candles[i]["high"] > recent_candles[i - 2]["high"]
                and recent_candles[i]["high"] > recent_candles[i + 1]["high"]
                and recent_candles[i]["high"] > recent_candles[i + 2]["high"]
            ):
                highs.append(recent_candles[i]["high"])

            # Локальный минимум
            if (
                recent_candles[i]["low"] < recent_candles[i - 1]["low"]
                and recent_candles[i]["low"] < recent_candles[i - 2]["low"]
                and recent_candles[i]["low"] < recent_candles[i + 1]["low"]
                and recent_candles[i]["low"] < recent_candles[i + 2]["low"]
            ):
                lows.append(recent_candles[i]["low"])

        # Кластеризация уровней
        def cluster_levels(levels: list[float], threshold: float) -> list[dict]:
            if not levels:
                return []

            levels = sorted(levels)
            clusters = []
            current_cluster = [levels[0]]

            for level in levels[1:]:
                if (level - current_cluster[-1]) / current_cluster[-1] < threshold:
                    current_cluster.append(level)
                else:
                    avg = sum(current_cluster) / len(current_cluster)
                    clusters.append(
                        {
                            "level": round(avg, 2),
                            "strength": len(current_cluster),
                            "touches": len(current_cluster),
                        }
                    )
                    current_cluster = [level]

            # Последний кластер
            if current_cluster:
                avg = sum(current_cluster) / len(current_cluster)
                clusters.append(
                    {
                        "level": round(avg, 2),
                        "strength": len(current_cluster),
                        "touches": len(current_cluster),
                    }
                )

            return sorted(clusters, key=lambda x: -x["strength"])

        current_price = candles[-1]["close"]

        resistance_levels = cluster_levels(highs, threshold_pct)
        support_levels = cluster_levels(lows, threshold_pct)

        # Фильтруем: сопротивление выше цены, поддержка ниже
        resistance = [r for r in resistance_levels if r["level"] > current_price]
        support = [s for s in support_levels if s["level"] < current_price]

        # Психологические уровни (круглые числа)
        psychological = TechnicalAnalyzer.find_psychological_levels(current_price)

        return {
            "resistance": resistance[:5],  # Топ 5
            "support": support[:5],
            "nearest_resistance": resistance[0] if resistance else None,
            "nearest_support": support[0] if support else None,
            "psychological": psychological,
            "current_price": current_price,
        }

    @staticmethod
    def find_psychological_levels(current_price: float, count: int = 3) -> dict:
        """
        Найти психологические уровни (круглые числа)

        Args:
            current_price: Текущая цена
            count: Количество уровней в каждую сторону

        Returns:
            Dict с психологическими уровнями выше и ниже цены
        """
        # Определяем порядок величины для уровней
        if current_price >= 50000:
            # BTC: уровни по 5000 (50k, 55k, 60k...)
            step = 5000
        elif current_price >= 10000:
            # 10k-50k: уровни по 2500
            step = 2500
        elif current_price >= 1000:
            # 1k-10k: уровни по 500
            step = 500
        elif current_price >= 100:
            # 100-1000: уровни по 50
            step = 50
        elif current_price >= 10:
            # 10-100: уровни по 5
            step = 5
        elif current_price >= 1:
            # 1-10: уровни по 0.5
            step = 0.5
        else:
            # < 1: уровни по 0.05
            step = 0.05

        # Находим ближайший круглый уровень
        base_level = (current_price // step) * step

        # Уровни выше цены
        resistance = []
        level = base_level + step if base_level < current_price else base_level
        while len(resistance) < count:
            if level > current_price:
                distance_pct = ((level - current_price) / current_price) * 100
                resistance.append(
                    {
                        "level": round(level, 2),
                        "type": "psychological",
                        "distance_pct": round(distance_pct, 2),
                    }
                )
            level += step

        # Уровни ниже цены
        support = []
        level = base_level if base_level < current_price else base_level - step
        while len(support) < count and level > 0:
            if level < current_price:
                distance_pct = ((current_price - level) / current_price) * 100
                support.append(
                    {
                        "level": round(level, 2),
                        "type": "psychological",
                        "distance_pct": round(distance_pct, 2),
                    }
                )
            level -= step

        return {
            "resistance": resistance,
            "support": support,
            "step": step,
            "note_ru": f"Круглые уровни с шагом {step:,.0f}",
        }

    # ========================================================================
    # ОСНОВНЫЕ МЕТОДЫ
    # ========================================================================

    def analyze(
        self, symbol: str, timeframe: str = "1d", candles: list[dict] = None
    ) -> TechnicalIndicators | None:
        """
        Полный технический анализ

        Args:
            symbol: Символ монеты
            timeframe: Таймфрейм
            candles: Список свечей (опционально, иначе из БД)

        Returns:
            TechnicalIndicators с рассчитанными индикаторами
        """
        # Получаем данные
        if candles is None:
            candles = self.db.get_ohlcv(symbol, timeframe, limit=250)

        if len(candles) < 26:
            logger.warning(f"Недостаточно данных для анализа {symbol}/{timeframe}")
            return None

        # Извлекаем цены
        closes = [c["close"] for c in candles]
        current_candle = candles[-1]

        # Создаём результат
        result = TechnicalIndicators(
            symbol=symbol.upper(),
            timeframe=timeframe,
            timestamp=current_candle["timestamp"],
            price=current_candle["close"],
        )

        # Moving Averages
        result.sma_20 = round(self.calc_sma(closes, 20), 2) if len(closes) >= 20 else None
        result.sma_50 = round(self.calc_sma(closes, 50), 2) if len(closes) >= 50 else None
        result.sma_200 = round(self.calc_sma(closes, 200), 2) if len(closes) >= 200 else None
        result.ema_12 = round(self.calc_ema(closes, 12), 2) if len(closes) >= 12 else None
        result.ema_26 = round(self.calc_ema(closes, 26), 2) if len(closes) >= 26 else None

        # RSI
        result.rsi = self.calc_rsi(closes, 14)

        # MACD
        macd_line, macd_signal, macd_hist = self.calc_macd(closes)
        result.macd_line = macd_line
        result.macd_signal = macd_signal
        result.macd_histogram = macd_hist

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower, bb_pos = self.calc_bollinger_bands(closes)
        result.bb_upper = bb_upper
        result.bb_middle = bb_middle
        result.bb_lower = bb_lower
        result.bb_position = bb_pos

        # ATR
        result.atr = self.calc_atr(candles, 14)

        # Volume
        volumes = [c["volume"] for c in candles]
        result.volume_sma = round(self.calc_sma(volumes, 20), 2) if len(volumes) >= 20 else None
        if result.volume_sma and result.volume_sma > 0:
            result.volume_ratio = round(volumes[-1] / result.volume_sma, 2)

        # Price changes
        if len(closes) >= 2:
            result.price_change_24h = round(((closes[-1] - closes[-2]) / closes[-2]) * 100, 2)
        if len(closes) >= 8:
            result.price_change_7d = round(((closes[-1] - closes[-8]) / closes[-8]) * 100, 2)

        return result

    def get_signal_summary(self, indicators: TechnicalIndicators) -> dict:
        """
        Получить интерпретацию сигналов

        Args:
            indicators: Рассчитанные индикаторы

        Returns:
            Словарь с интерпретацией
        """
        signals = {"overall": "neutral", "overall_ru": "Нейтрально", "score": 50, "details": []}

        score = 50  # Начинаем с нейтрального

        # RSI
        if indicators.rsi:
            if indicators.rsi < 30:
                signals["details"].append(
                    {
                        "indicator": "RSI",
                        "value": indicators.rsi,
                        "signal": "bullish",
                        "signal_ru": f"Перепродан ({indicators.rsi:.0f})",
                        "description": "RSI в зоне перепроданности - возможен отскок",
                    }
                )
                score += 15
            elif indicators.rsi > 70:
                signals["details"].append(
                    {
                        "indicator": "RSI",
                        "value": indicators.rsi,
                        "signal": "bearish",
                        "signal_ru": f"Перекуплен ({indicators.rsi:.0f})",
                        "description": "RSI в зоне перекупленности - возможна коррекция",
                    }
                )
                score -= 15
            else:
                signals["details"].append(
                    {
                        "indicator": "RSI",
                        "value": indicators.rsi,
                        "signal": "neutral",
                        "signal_ru": f"Нейтрально ({indicators.rsi:.0f})",
                        "description": "RSI в нейтральной зоне",
                    }
                )

        # SMA200 Trend
        if indicators.sma_200 and indicators.price:
            if indicators.price > indicators.sma_200:
                signals["details"].append(
                    {
                        "indicator": "SMA200",
                        "value": indicators.sma_200,
                        "signal": "bullish",
                        "signal_ru": "Выше SMA200",
                        "description": "Цена выше долгосрочной средней - бычий тренд",
                    }
                )
                score += 10
            else:
                signals["details"].append(
                    {
                        "indicator": "SMA200",
                        "value": indicators.sma_200,
                        "signal": "bearish",
                        "signal_ru": "Ниже SMA200",
                        "description": "Цена ниже долгосрочной средней - медвежий тренд",
                    }
                )
                score -= 10

        # Golden/Death Cross
        if indicators.sma_50 and indicators.sma_200:
            if indicators.sma_50 > indicators.sma_200:
                signals["details"].append(
                    {
                        "indicator": "MA Cross",
                        "signal": "bullish",
                        "signal_ru": "Golden Cross активен",
                        "description": "SMA50 выше SMA200 - бычий сигнал",
                    }
                )
                score += 10
            else:
                signals["details"].append(
                    {
                        "indicator": "MA Cross",
                        "signal": "bearish",
                        "signal_ru": "Death Cross активен",
                        "description": "SMA50 ниже SMA200 - медвежий сигнал",
                    }
                )
                score -= 10

        # MACD
        if indicators.macd_histogram is not None:
            if indicators.macd_histogram > 0:
                signals["details"].append(
                    {
                        "indicator": "MACD",
                        "value": indicators.macd_histogram,
                        "signal": "bullish",
                        "signal_ru": "MACD положительный",
                        "description": "Бычий моментум",
                    }
                )
                score += 5
            else:
                signals["details"].append(
                    {
                        "indicator": "MACD",
                        "value": indicators.macd_histogram,
                        "signal": "bearish",
                        "signal_ru": "MACD отрицательный",
                        "description": "Медвежий моментум",
                    }
                )
                score -= 5

        # Bollinger Bands
        if indicators.bb_position is not None:
            if indicators.bb_position < 20:
                signals["details"].append(
                    {
                        "indicator": "Bollinger",
                        "value": indicators.bb_position,
                        "signal": "bullish",
                        "signal_ru": "У нижней границы BB",
                        "description": "Цена у нижней границы Bollinger - возможен отскок",
                    }
                )
                score += 5
            elif indicators.bb_position > 80:
                signals["details"].append(
                    {
                        "indicator": "Bollinger",
                        "value": indicators.bb_position,
                        "signal": "bearish",
                        "signal_ru": "У верхней границы BB",
                        "description": "Цена у верхней границы Bollinger - возможен откат",
                    }
                )
                score -= 5

        # Volume
        if indicators.volume_ratio:
            if indicators.volume_ratio > 1.5:
                signals["details"].append(
                    {
                        "indicator": "Volume",
                        "value": indicators.volume_ratio,
                        "signal": "high",
                        "signal_ru": f"Объём x{indicators.volume_ratio:.1f}",
                        "description": "Повышенный объём - подтверждение движения",
                    }
                )

        # Финальный score
        score = max(0, min(100, score))
        signals["score"] = score

        if score >= 70:
            signals["overall"] = "bullish"
            signals["overall_ru"] = "Бычий"
        elif score >= 55:
            signals["overall"] = "slightly_bullish"
            signals["overall_ru"] = "Умеренно бычий"
        elif score <= 30:
            signals["overall"] = "bearish"
            signals["overall_ru"] = "Медвежий"
        elif score <= 45:
            signals["overall"] = "slightly_bearish"
            signals["overall_ru"] = "Умеренно медвежий"
        else:
            signals["overall"] = "neutral"
            signals["overall_ru"] = "Нейтрально"

        return signals

    def analyze_full(self, symbol: str, timeframe: str = "1d") -> dict:
        """
        Полный анализ с интерпретацией

        Returns:
            Словарь с индикаторами и интерпретацией
        """
        indicators = self.analyze(symbol, timeframe)

        if not indicators:
            return {"error": f"Недостаточно данных для {symbol}/{timeframe}"}

        candles = self.db.get_ohlcv(symbol, timeframe, limit=100)
        sr_levels = self.find_support_resistance(candles)

        signals = self.get_signal_summary(indicators)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": indicators.timestamp,
            "price": indicators.price,
            "indicators": indicators.to_dict(),
            "signals": signals,
            "support_resistance": sr_levels,
            "updated_at": datetime.now().isoformat(),
        }


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO)

    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1d"

    analyzer = TechnicalAnalyzer()
    result = analyzer.analyze_full(symbol, timeframe)

    print(json.dumps(result, indent=2, default=str))
