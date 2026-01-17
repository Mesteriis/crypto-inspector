"""
Pattern Detector - Обнаружение технических паттернов

Паттерны:
- Double Top / Double Bottom
- Golden Cross / Death Cross
- RSI Divergence (bullish/bearish)
- Trend patterns (N дней роста/падения)
- Support/Resistance breakouts
- Higher Highs / Lower Lows

Каждый паттерн включает:
- Описание на русском
- Исторический контекст (когда был последний раз)
- Результат после предыдущего сигнала
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from analysis import TechnicalAnalyzer
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


@dataclass
class PatternSignal:
    """Структура обнаруженного паттерна"""

    pattern_type: str
    pattern_name: str
    pattern_name_ru: str
    direction: str  # 'bullish', 'bearish', 'neutral'
    strength: int  # 1-10
    description: str
    description_ru: str

    # Исторический контекст
    last_occurrence_days: int | None = None
    last_occurrence_result: float | None = None  # % изменения после
    last_occurrence_period: int | None = None  # дней до результата
    historical_win_rate: float | None = None
    historical_avg_result: float | None = None

    # Текущие данные
    current_price: float = 0
    trigger_price: float | None = None
    target_price: float | None = None

    timestamp: int = 0

    def to_dict(self) -> dict:
        return {
            "type": self.pattern_type,
            "name": self.pattern_name,
            "name_ru": self.pattern_name_ru,
            "direction": self.direction,
            "strength": self.strength,
            "description": self.description,
            "description_ru": self.description_ru,
            "last_occurrence": {
                "days_ago": self.last_occurrence_days,
                "result_pct": self.last_occurrence_result,
                "result_period_days": self.last_occurrence_period,
            },
            "statistics": {
                "win_rate": self.historical_win_rate,
                "avg_result": self.historical_avg_result,
            },
            "prices": {
                "current": self.current_price,
                "trigger": self.trigger_price,
                "target": self.target_price,
            },
            "timestamp": self.timestamp,
        }

    def get_alert_message(self) -> str:
        """Сформировать сообщение для уведомления"""
        msg = f"**{self.pattern_name_ru}**\n\n"
        msg += f"{self.description_ru}\n\n"

        if self.last_occurrence_days:
            msg += f"📊 Последний раз: {self.last_occurrence_days} дней назад\n"
            if self.last_occurrence_result:
                sign = "+" if self.last_occurrence_result > 0 else ""
                msg += f"Результат тогда: {sign}{self.last_occurrence_result:.1f}% "
                if self.last_occurrence_period:
                    msg += f"за {self.last_occurrence_period} дней\n"

        if self.historical_win_rate:
            msg += f"\n📈 Win rate: {self.historical_win_rate:.0f}%"
        if self.historical_avg_result:
            sign = "+" if self.historical_avg_result > 0 else ""
            msg += f" | Средний результат: {sign}{self.historical_avg_result:.1f}%"

        return msg


class PatternDetector:
    """Детектор технических паттернов"""

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self.ta = TechnicalAnalyzer(self.db)

    def detect_all(self, symbol: str, timeframe: str = "1d") -> list[PatternSignal]:
        """
        Обнаружить все паттерны для символа

        Args:
            symbol: Символ монеты
            timeframe: Таймфрейм

        Returns:
            Список обнаруженных паттернов
        """
        patterns = []

        # Получаем данные
        candles = self.db.get_ohlcv(symbol, timeframe, limit=250)
        if len(candles) < 50:
            logger.warning(f"Недостаточно данных для {symbol}/{timeframe}")
            return patterns

        closes = [c["close"] for c in candles]
        current_price = closes[-1]
        timestamp = candles[-1]["timestamp"]

        # Рассчитываем индикаторы
        indicators = self.ta.analyze(symbol, timeframe, candles)

        # === GOLDEN CROSS / DEATH CROSS ===
        cross_pattern = self._detect_ma_cross(candles, symbol, timeframe)
        if cross_pattern:
            cross_pattern.current_price = current_price
            cross_pattern.timestamp = timestamp
            patterns.append(cross_pattern)

        # === RSI EXTREMES ===
        rsi_pattern = self._detect_rsi_extreme(indicators, symbol, timeframe)
        if rsi_pattern:
            rsi_pattern.current_price = current_price
            rsi_pattern.timestamp = timestamp
            patterns.append(rsi_pattern)

        # === TREND (N дней роста/падения) ===
        trend_pattern = self._detect_trend_streak(candles, symbol, timeframe)
        if trend_pattern:
            trend_pattern.current_price = current_price
            trend_pattern.timestamp = timestamp
            patterns.append(trend_pattern)

        # === DOUBLE TOP / DOUBLE BOTTOM ===
        double_pattern = self._detect_double_pattern(candles, symbol, timeframe)
        if double_pattern:
            double_pattern.current_price = current_price
            double_pattern.timestamp = timestamp
            patterns.append(double_pattern)

        # === BOLLINGER SQUEEZE / BREAKOUT ===
        bb_pattern = self._detect_bollinger_pattern(candles, indicators, symbol, timeframe)
        if bb_pattern:
            bb_pattern.current_price = current_price
            bb_pattern.timestamp = timestamp
            patterns.append(bb_pattern)

        # === SUPPORT/RESISTANCE BREAKOUT ===
        sr_pattern = self._detect_sr_breakout(candles, symbol, timeframe)
        if sr_pattern:
            sr_pattern.current_price = current_price
            sr_pattern.timestamp = timestamp
            patterns.append(sr_pattern)

        # === HIGHER HIGHS / LOWER LOWS ===
        hh_ll_pattern = self._detect_hh_ll(candles, symbol, timeframe)
        if hh_ll_pattern:
            hh_ll_pattern.current_price = current_price
            hh_ll_pattern.timestamp = timestamp
            patterns.append(hh_ll_pattern)

        return patterns

    def _detect_ma_cross(
        self, candles: list[dict], symbol: str, timeframe: str
    ) -> PatternSignal | None:
        """Обнаружить Golden Cross / Death Cross"""
        if len(candles) < 210:
            return None

        closes = [c["close"] for c in candles]

        # SMA50 и SMA200 для последних двух дней
        sma50_today = self.ta.calc_sma(closes, 50)
        sma200_today = self.ta.calc_sma(closes, 200)

        sma50_yesterday = self.ta.calc_sma(closes[:-1], 50)
        sma200_yesterday = self.ta.calc_sma(closes[:-1], 200)

        if not all([sma50_today, sma200_today, sma50_yesterday, sma200_yesterday]):
            return None

        # Golden Cross: SMA50 пересекает SMA200 снизу вверх
        if sma50_yesterday < sma200_yesterday and sma50_today > sma200_today:
            history = self._get_pattern_history(symbol, "golden_cross")

            return PatternSignal(
                pattern_type="golden_cross",
                pattern_name="Golden Cross",
                pattern_name_ru="🟢 Золотой крест",
                direction="bullish",
                strength=8,
                description="SMA50 crossed above SMA200",
                description_ru="SMA50 пересёк SMA200 снизу вверх. Сильный бычий сигнал.",
                last_occurrence_days=history.get("days_ago"),
                last_occurrence_result=history.get("result_30d"),
                last_occurrence_period=30,
                historical_win_rate=history.get("win_rate"),
                historical_avg_result=history.get("avg_result"),
            )

        # Death Cross: SMA50 пересекает SMA200 сверху вниз
        if sma50_yesterday > sma200_yesterday and sma50_today < sma200_today:
            history = self._get_pattern_history(symbol, "death_cross")

            return PatternSignal(
                pattern_type="death_cross",
                pattern_name="Death Cross",
                pattern_name_ru="🔴 Крест смерти",
                direction="bearish",
                strength=8,
                description="SMA50 crossed below SMA200",
                description_ru="SMA50 пересёк SMA200 сверху вниз. Сильный медвежий сигнал.",
                last_occurrence_days=history.get("days_ago"),
                last_occurrence_result=history.get("result_30d"),
                last_occurrence_period=30,
                historical_win_rate=history.get("win_rate"),
                historical_avg_result=history.get("avg_result"),
            )

        # Проверяем активный статус (не пересечение, но сигнал активен)
        if sma50_today > sma200_today:
            # Golden Cross активен, но не новый
            return None  # Не сигнализируем о "продолжении"

        return None

    def _detect_rsi_extreme(self, indicators, symbol: str, timeframe: str) -> PatternSignal | None:
        """Обнаружить RSI в экстремальных зонах"""
        if not indicators or not indicators.rsi:
            return None

        rsi = indicators.rsi

        # RSI Oversold (< 30)
        if rsi < 30:
            history = self._get_pattern_history(symbol, "rsi_oversold")

            return PatternSignal(
                pattern_type="rsi_oversold",
                pattern_name="RSI Oversold",
                pattern_name_ru=f"🟢 RSI перепродан ({rsi:.0f})",
                direction="bullish",
                strength=6 if rsi < 25 else 5,
                description=f"RSI at {rsi:.1f} (oversold zone)",
                description_ru=f"RSI = {rsi:.0f} в зоне перепроданности. Возможен отскок.",
                last_occurrence_days=history.get("days_ago"),
                last_occurrence_result=history.get("result_7d"),
                last_occurrence_period=7,
                historical_win_rate=history.get("win_rate"),
                historical_avg_result=history.get("avg_result"),
            )

        # RSI Overbought (> 70)
        if rsi > 70:
            history = self._get_pattern_history(symbol, "rsi_overbought")

            return PatternSignal(
                pattern_type="rsi_overbought",
                pattern_name="RSI Overbought",
                pattern_name_ru=f"🔴 RSI перекуплен ({rsi:.0f})",
                direction="bearish",
                strength=6 if rsi > 75 else 5,
                description=f"RSI at {rsi:.1f} (overbought zone)",
                description_ru=f"RSI = {rsi:.0f} в зоне перекупленности. Возможна коррекция.",
                last_occurrence_days=history.get("days_ago"),
                last_occurrence_result=history.get("result_7d"),
                last_occurrence_period=7,
                historical_win_rate=history.get("win_rate"),
                historical_avg_result=history.get("avg_result"),
            )

        return None

    def _detect_trend_streak(
        self, candles: list[dict], symbol: str, timeframe: str
    ) -> PatternSignal | None:
        """Обнаружить серию дней роста/падения"""
        if len(candles) < 10:
            return None

        # Считаем последовательные дни роста/падения
        up_days = 0
        down_days = 0
        total_change = 0

        for i in range(len(candles) - 1, 0, -1):
            change = candles[i]["close"] - candles[i - 1]["close"]

            if change > 0:
                if down_days > 0:
                    break
                up_days += 1
                total_change += change
            elif change < 0:
                if up_days > 0:
                    break
                down_days += 1
                total_change += change
            else:
                break

        # Минимум 5 дней для сигнала
        if up_days >= 5:
            pct_change = (total_change / candles[-up_days - 1]["close"]) * 100
            history = self._get_pattern_history(symbol, "trend_up")

            return PatternSignal(
                pattern_type="trend_up",
                pattern_name=f"{up_days}-Day Uptrend",
                pattern_name_ru=f"📈 Рост {up_days} дней подряд",
                direction="bullish",
                strength=min(8, 4 + up_days // 2),
                description=f"{up_days} consecutive up days (+{pct_change:.1f}%)",
                description_ru=f"Растём {up_days} дней подряд (+{pct_change:.1f}%). "
                f"Возможно продолжение или коррекция для фиксации.",
                last_occurrence_days=history.get("days_ago"),
                last_occurrence_result=history.get("result_7d"),
                last_occurrence_period=7,
                historical_win_rate=history.get("win_rate"),
                historical_avg_result=history.get("avg_result"),
            )

        if down_days >= 5:
            pct_change = (total_change / candles[-down_days - 1]["close"]) * 100
            history = self._get_pattern_history(symbol, "trend_down")

            return PatternSignal(
                pattern_type="trend_down",
                pattern_name=f"{down_days}-Day Downtrend",
                pattern_name_ru=f"📉 Падение {down_days} дней подряд",
                direction="bearish",
                strength=min(8, 4 + down_days // 2),
                description=f"{down_days} consecutive down days ({pct_change:.1f}%)",
                description_ru=f"Падаем {down_days} дней подряд ({pct_change:.1f}%). "
                f"Возможен отскок или продолжение падения.",
                last_occurrence_days=history.get("days_ago"),
                last_occurrence_result=history.get("result_7d"),
                last_occurrence_period=7,
                historical_win_rate=history.get("win_rate"),
                historical_avg_result=history.get("avg_result"),
            )

        return None

    def _detect_double_pattern(
        self, candles: list[dict], symbol: str, timeframe: str
    ) -> PatternSignal | None:
        """Обнаружить Double Top / Double Bottom"""
        if len(candles) < 30:
            return None

        highs = [c["high"] for c in candles[-30:]]
        lows = [c["low"] for c in candles[-30:]]
        closes = [c["close"] for c in candles[-30:]]

        current_price = closes[-1]

        # Находим два максимума
        max1_idx = highs.index(max(highs[:15]))
        max2_idx = 15 + highs[15:].index(max(highs[15:]))

        max1 = highs[max1_idx]
        max2 = highs[max2_idx]

        # Double Top: два близких максимума, цена падает
        if abs(max1 - max2) / max1 < 0.03:  # Разница < 3%
            neckline = (
                min(lows[max1_idx:max2_idx])
                if max1_idx < max2_idx
                else min(lows[max2_idx:max1_idx])
            )

            if current_price < neckline:
                history = self._get_pattern_history(symbol, "double_top")

                return PatternSignal(
                    pattern_type="double_top",
                    pattern_name="Double Top",
                    pattern_name_ru="🔴 Двойная вершина",
                    direction="bearish",
                    strength=7,
                    description=f"Double top at ~${max1:,.0f}, neckline broken",
                    description_ru=f"Двойная вершина на ~${max1:,.0f}. "
                    f"Пробита линия шеи ${neckline:,.0f}. Медвежий сигнал.",
                    trigger_price=neckline,
                    target_price=neckline - (max1 - neckline),
                    last_occurrence_days=history.get("days_ago"),
                    last_occurrence_result=history.get("result_30d"),
                    last_occurrence_period=30,
                    historical_win_rate=history.get("win_rate"),
                    historical_avg_result=history.get("avg_result"),
                )

        # Находим два минимума
        min1_idx = lows.index(min(lows[:15]))
        min2_idx = 15 + lows[15:].index(min(lows[15:]))

        min1 = lows[min1_idx]
        min2 = lows[min2_idx]

        # Double Bottom: два близких минимума, цена растёт
        if abs(min1 - min2) / min1 < 0.03:
            neckline = (
                max(highs[min1_idx:min2_idx])
                if min1_idx < min2_idx
                else max(highs[min2_idx:min1_idx])
            )

            if current_price > neckline:
                history = self._get_pattern_history(symbol, "double_bottom")

                return PatternSignal(
                    pattern_type="double_bottom",
                    pattern_name="Double Bottom",
                    pattern_name_ru="🟢 Двойное дно",
                    direction="bullish",
                    strength=7,
                    description=f"Double bottom at ~${min1:,.0f}, neckline broken",
                    description_ru=f"Двойное дно на ~${min1:,.0f}. "
                    f"Пробита линия шеи ${neckline:,.0f}. Бычий сигнал.",
                    trigger_price=neckline,
                    target_price=neckline + (neckline - min1),
                    last_occurrence_days=history.get("days_ago"),
                    last_occurrence_result=history.get("result_30d"),
                    last_occurrence_period=30,
                    historical_win_rate=history.get("win_rate"),
                    historical_avg_result=history.get("avg_result"),
                )

        return None

    def _detect_bollinger_pattern(
        self, candles: list[dict], indicators, symbol: str, timeframe: str
    ) -> PatternSignal | None:
        """Обнаружить Bollinger Squeeze / Breakout"""
        if not indicators or not indicators.bb_upper:
            return None

        current_price = candles[-1]["close"]
        prev_price = candles[-2]["close"]

        # Breakout выше верхней границы
        if current_price > indicators.bb_upper and prev_price <= indicators.bb_upper:
            history = self._get_pattern_history(symbol, "bb_breakout_up")

            return PatternSignal(
                pattern_type="bb_breakout_up",
                pattern_name="Bollinger Breakout Up",
                pattern_name_ru="📈 Пробой верхней BB",
                direction="bullish",
                strength=6,
                description=f"Price broke above upper BB (${indicators.bb_upper:,.0f})",
                description_ru=f"Цена пробила верхнюю границу Bollinger (${indicators.bb_upper:,.0f}). "
                f"Возможно продолжение импульса.",
                trigger_price=indicators.bb_upper,
                last_occurrence_days=history.get("days_ago"),
                last_occurrence_result=history.get("result_7d"),
                last_occurrence_period=7,
                historical_win_rate=history.get("win_rate"),
                historical_avg_result=history.get("avg_result"),
            )

        # Breakout ниже нижней границы
        if current_price < indicators.bb_lower and prev_price >= indicators.bb_lower:
            history = self._get_pattern_history(symbol, "bb_breakout_down")

            return PatternSignal(
                pattern_type="bb_breakout_down",
                pattern_name="Bollinger Breakout Down",
                pattern_name_ru="📉 Пробой нижней BB",
                direction="bearish",
                strength=6,
                description=f"Price broke below lower BB (${indicators.bb_lower:,.0f})",
                description_ru=f"Цена пробила нижнюю границу Bollinger (${indicators.bb_lower:,.0f}). "
                f"Возможно продолжение падения или отскок.",
                trigger_price=indicators.bb_lower,
                last_occurrence_days=history.get("days_ago"),
                last_occurrence_result=history.get("result_7d"),
                last_occurrence_period=7,
                historical_win_rate=history.get("win_rate"),
                historical_avg_result=history.get("avg_result"),
            )

        return None

    def _detect_sr_breakout(
        self, candles: list[dict], symbol: str, timeframe: str
    ) -> PatternSignal | None:
        """Обнаружить пробой поддержки/сопротивления"""
        sr_levels = self.ta.find_support_resistance(candles, lookback=60)

        current_price = candles[-1]["close"]
        prev_price = candles[-2]["close"]

        # Проверяем пробой сопротивления
        nearest_res = sr_levels.get("nearest_resistance")
        if nearest_res:
            level = nearest_res["level"]
            if prev_price < level and current_price > level:
                history = self._get_pattern_history(symbol, "resistance_break")

                return PatternSignal(
                    pattern_type="resistance_break",
                    pattern_name="Resistance Breakout",
                    pattern_name_ru=f"🟢 Пробой сопротивления ${level:,.0f}",
                    direction="bullish",
                    strength=5 + nearest_res["strength"],
                    description=f'Broke resistance at ${level:,.0f} ({nearest_res["touches"]} touches)',
                    description_ru=f'Пробито сопротивление ${level:,.0f} '
                    f'({nearest_res["touches"]} касаний). Бычий сигнал.',
                    trigger_price=level,
                    last_occurrence_days=history.get("days_ago"),
                    last_occurrence_result=history.get("result_7d"),
                    last_occurrence_period=7,
                    historical_win_rate=history.get("win_rate"),
                    historical_avg_result=history.get("avg_result"),
                )

        # Проверяем пробой поддержки
        nearest_sup = sr_levels.get("nearest_support")
        if nearest_sup:
            level = nearest_sup["level"]
            if prev_price > level and current_price < level:
                history = self._get_pattern_history(symbol, "support_break")

                return PatternSignal(
                    pattern_type="support_break",
                    pattern_name="Support Breakdown",
                    pattern_name_ru=f"🔴 Пробой поддержки ${level:,.0f}",
                    direction="bearish",
                    strength=5 + nearest_sup["strength"],
                    description=f'Broke support at ${level:,.0f} ({nearest_sup["touches"]} touches)',
                    description_ru=f'Пробита поддержка ${level:,.0f} '
                    f'({nearest_sup["touches"]} касаний). Медвежий сигнал.',
                    trigger_price=level,
                    last_occurrence_days=history.get("days_ago"),
                    last_occurrence_result=history.get("result_7d"),
                    last_occurrence_period=7,
                    historical_win_rate=history.get("win_rate"),
                    historical_avg_result=history.get("avg_result"),
                )

        return None

    def _detect_hh_ll(
        self, candles: list[dict], symbol: str, timeframe: str
    ) -> PatternSignal | None:
        """Обнаружить Higher Highs / Lower Lows"""
        if len(candles) < 20:
            return None

        # Находим последние 4 swing high/low
        swing_highs = []
        swing_lows = []

        for i in range(2, len(candles) - 2):
            # Swing High
            if (
                candles[i]["high"] > candles[i - 1]["high"]
                and candles[i]["high"] > candles[i - 2]["high"]
                and candles[i]["high"] > candles[i + 1]["high"]
                and candles[i]["high"] > candles[i + 2]["high"]
            ):
                swing_highs.append((i, candles[i]["high"]))

            # Swing Low
            if (
                candles[i]["low"] < candles[i - 1]["low"]
                and candles[i]["low"] < candles[i - 2]["low"]
                and candles[i]["low"] < candles[i + 1]["low"]
                and candles[i]["low"] < candles[i + 2]["low"]
            ):
                swing_lows.append((i, candles[i]["low"]))

        # Берём последние 3
        recent_highs = swing_highs[-3:] if len(swing_highs) >= 3 else []
        recent_lows = swing_lows[-3:] if len(swing_lows) >= 3 else []

        # Higher Highs
        if len(recent_highs) >= 3:
            if recent_highs[-1][1] > recent_highs[-2][1] > recent_highs[-3][1]:
                return PatternSignal(
                    pattern_type="higher_highs",
                    pattern_name="Higher Highs",
                    pattern_name_ru="📈 Растущие максимумы",
                    direction="bullish",
                    strength=6,
                    description="Forming higher highs - uptrend confirmation",
                    description_ru="Формируются растущие максимумы. Подтверждение восходящего тренда.",
                )

        # Lower Lows
        if len(recent_lows) >= 3:
            if recent_lows[-1][1] < recent_lows[-2][1] < recent_lows[-3][1]:
                return PatternSignal(
                    pattern_type="lower_lows",
                    pattern_name="Lower Lows",
                    pattern_name_ru="📉 Падающие минимумы",
                    direction="bearish",
                    strength=6,
                    description="Forming lower lows - downtrend confirmation",
                    description_ru="Формируются падающие минимумы. Подтверждение нисходящего тренда.",
                )

        return None

    def _get_pattern_history(self, symbol: str, pattern_type: str) -> dict:
        """
        Получить историю паттерна из БД

        Returns:
            Dict с days_ago, result_7d, result_30d, win_rate, avg_result
        """
        signals = self.db.get_signal_history(symbol, pattern_type, limit=10)

        if not signals:
            return {}

        last_signal = signals[0]

        # Дней назад
        try:
            signal_date = datetime.strptime(last_signal["signal_date"], "%Y-%m-%d")
            days_ago = (datetime.now() - signal_date).days
        except:
            days_ago = None

        # Статистика
        results_7d = [s["result_7d"] for s in signals if s.get("result_7d") is not None]
        results_30d = [s["result_30d"] for s in signals if s.get("result_30d") is not None]

        win_rate = None
        avg_result = None

        if results_30d:
            # Для бычьих паттернов win = положительный результат
            # Для медвежьих - отрицательный
            if "bullish" in pattern_type or pattern_type in [
                "golden_cross",
                "double_bottom",
                "rsi_oversold",
                "trend_up",
                "resistance_break",
                "higher_highs",
            ]:
                wins = sum(1 for r in results_30d if r > 0)
            else:
                wins = sum(1 for r in results_30d if r < 0)

            win_rate = (wins / len(results_30d)) * 100
            avg_result = sum(results_30d) / len(results_30d)

        return {
            "days_ago": days_ago,
            "result_7d": last_signal.get("result_7d"),
            "result_30d": last_signal.get("result_30d"),
            "win_rate": win_rate,
            "avg_result": avg_result,
        }

    def save_detected_patterns(
        self, symbol: str, patterns: list[PatternSignal], timeframe: str = "1d"
    ):
        """Сохранить обнаруженные паттерны в БД"""
        for pattern in patterns:
            self.db.insert_signal(
                symbol=symbol,
                signal_type=pattern.pattern_type,
                signal_date=datetime.now().strftime("%Y-%m-%d"),
                price=pattern.current_price,
                direction=pattern.direction,
                strength=pattern.strength,
                description=pattern.description,
                description_ru=pattern.description_ru,
                timeframe=timeframe,
            )


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO)

    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTC"

    detector = PatternDetector()
    patterns = detector.detect_all(symbol)

    print(f"\n📊 Обнаруженные паттерны для {symbol}:")
    print("=" * 60)

    if not patterns:
        print("Паттернов не обнаружено")
    else:
        for p in patterns:
            print(f"\n{p.pattern_name_ru}")
            print(f"  Направление: {p.direction}")
            print(f"  Сила: {p.strength}/10")
            print(f"  {p.description_ru}")
            if p.last_occurrence_days:
                print(f"  Последний раз: {p.last_occurrence_days} дней назад")
            if p.historical_win_rate:
                print(f"  Win rate: {p.historical_win_rate:.0f}%")

    print("\n" + "=" * 60)
    print("\nJSON:")
    print(json.dumps([p.to_dict() for p in patterns], indent=2, ensure_ascii=False))
