"""Human-readable explanations for all metrics.

Provides context and action suggestions for every indicator
in both English and Russian.
"""

import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


# =============================================================================
# Explanation Data Structure
# =============================================================================


@dataclass
class MetricExplanation:
    """Explanation for a metric value."""

    zone: str  # e.g., "oversold", "overbought", "neutral"
    zone_en: str
    zone_ru: str
    explanation: str
    explanation_ru: str
    action: str
    action_ru: str
    severity: Literal["info", "warning", "opportunity", "danger"]


# =============================================================================
# Explanation Database
# =============================================================================

EXPLANATIONS = {
    # -------------------------------------------------------------------------
    # RSI (Relative Strength Index)
    # -------------------------------------------------------------------------
    "rsi": {
        "ranges": [
            {
                "min": 0,
                "max": 20,
                "zone": "extreme_oversold",
                "zone_en": "Extremely Oversold",
                "zone_ru": "Экстремальная перепроданность",
                "explanation_en": "RSI below 20 indicates extreme oversold conditions. This is rare and often signals a strong reversal opportunity.",
                "explanation_ru": "RSI ниже 20 указывает на экстремальную перепроданность. Это редкость и часто сигнализирует о возможности сильного разворота.",
                "action_en": "Strong buy signal - consider accumulating",
                "action_ru": "Сильный сигнал на покупку - рассмотрите накопление",
                "severity": "opportunity",
            },
            {
                "min": 20,
                "max": 30,
                "zone": "oversold",
                "zone_en": "Oversold",
                "zone_ru": "Перепроданность",
                "explanation_en": "RSI below 30 indicates oversold conditions. Historically a good buying opportunity.",
                "explanation_ru": "RSI ниже 30 указывает на перепроданность. Исторически хорошая возможность для покупки.",
                "action_en": "Consider buying or DCA",
                "action_ru": "Рассмотрите покупку или DCA",
                "severity": "opportunity",
            },
            {
                "min": 30,
                "max": 45,
                "zone": "weak",
                "zone_en": "Weak",
                "zone_ru": "Слабый",
                "explanation_en": "RSI in the lower range. Momentum is weak but not yet oversold.",
                "explanation_ru": "RSI в нижнем диапазоне. Импульс слабый, но ещё не перепродан.",
                "action_en": "Watch for further weakness or reversal",
                "action_ru": "Следите за дальнейшим ослаблением или разворотом",
                "severity": "info",
            },
            {
                "min": 45,
                "max": 55,
                "zone": "neutral",
                "zone_en": "Neutral",
                "zone_ru": "Нейтральный",
                "explanation_en": "RSI is balanced. No strong momentum in either direction.",
                "explanation_ru": "RSI сбалансирован. Нет сильного импульса в любом направлении.",
                "action_en": "Wait for clearer signals",
                "action_ru": "Дождитесь более чётких сигналов",
                "severity": "info",
            },
            {
                "min": 55,
                "max": 70,
                "zone": "strong",
                "zone_en": "Strong",
                "zone_ru": "Сильный",
                "explanation_en": "RSI shows strength. Bullish momentum is present.",
                "explanation_ru": "RSI показывает силу. Присутствует бычий импульс.",
                "action_en": "Trend is your friend - hold or add",
                "action_ru": "Тренд ваш друг - держите или добавляйте",
                "severity": "info",
            },
            {
                "min": 70,
                "max": 80,
                "zone": "overbought",
                "zone_en": "Overbought",
                "zone_ru": "Перекупленность",
                "explanation_en": "RSI above 70 indicates overbought conditions. Consider taking some profits.",
                "explanation_ru": "RSI выше 70 указывает на перекупленность. Рассмотрите частичную фиксацию прибыли.",
                "action_en": "Consider scaling out positions",
                "action_ru": "Рассмотрите частичное закрытие позиций",
                "severity": "warning",
            },
            {
                "min": 80,
                "max": 100,
                "zone": "extreme_overbought",
                "zone_en": "Extremely Overbought",
                "zone_ru": "Экстремальная перекупленность",
                "explanation_en": "RSI above 80 indicates extreme overbought conditions. High risk of correction.",
                "explanation_ru": "RSI выше 80 указывает на экстремальную перекупленность. Высокий риск коррекции.",
                "action_en": "Take profits - correction likely",
                "action_ru": "Зафиксируйте прибыль - вероятна коррекция",
                "severity": "danger",
            },
        ],
    },
    # -------------------------------------------------------------------------
    # Fear & Greed Index
    # -------------------------------------------------------------------------
    "fear_greed": {
        "ranges": [
            {
                "min": 0,
                "max": 20,
                "zone": "extreme_fear",
                "zone_en": "Extreme Fear",
                "zone_ru": "Экстремальный страх",
                "explanation_en": "Extreme fear often indicates a market bottom. Historically one of the best times to buy.",
                "explanation_ru": "Экстремальный страх часто указывает на дно рынка. Исторически одно из лучших времён для покупки.",
                "action_en": "Strong buying opportunity - be greedy when others are fearful",
                "action_ru": "Отличная возможность для покупки - будьте жадными, когда другие боятся",
                "severity": "opportunity",
            },
            {
                "min": 20,
                "max": 40,
                "zone": "fear",
                "zone_en": "Fear",
                "zone_ru": "Страх",
                "explanation_en": "Fear in the market. Good time to accumulate if you believe in long-term value.",
                "explanation_ru": "Страх на рынке. Хорошее время для накопления, если верите в долгосрочную ценность.",
                "action_en": "Consider DCA - accumulation zone",
                "action_ru": "Рассмотрите DCA - зона накопления",
                "severity": "opportunity",
            },
            {
                "min": 40,
                "max": 60,
                "zone": "neutral",
                "zone_en": "Neutral",
                "zone_ru": "Нейтральный",
                "explanation_en": "Market sentiment is balanced. No extreme emotions driving prices.",
                "explanation_ru": "Настроение рынка сбалансировано. Нет экстремальных эмоций, влияющих на цены.",
                "action_en": "Standard operations - follow your strategy",
                "action_ru": "Стандартные операции - следуйте своей стратегии",
                "severity": "info",
            },
            {
                "min": 60,
                "max": 80,
                "zone": "greed",
                "zone_en": "Greed",
                "zone_ru": "Жадность",
                "explanation_en": "Greed is building. Be cautious with new positions.",
                "explanation_ru": "Жадность нарастает. Будьте осторожны с новыми позициями.",
                "action_en": "Be careful with new buys - consider securing profits",
                "action_ru": "Будьте осторожны с новыми покупками - рассмотрите фиксацию прибыли",
                "severity": "warning",
            },
            {
                "min": 80,
                "max": 100,
                "zone": "extreme_greed",
                "zone_en": "Extreme Greed",
                "zone_ru": "Экстремальная жадность",
                "explanation_en": "Extreme greed often precedes corrections. Be fearful when others are greedy.",
                "explanation_ru": "Экстремальная жадность часто предшествует коррекциям. Бойтесь, когда другие жадные.",
                "action_en": "Take profits - market likely overheated",
                "action_ru": "Зафиксируйте прибыль - рынок вероятно перегрет",
                "severity": "danger",
            },
        ],
    },
    # -------------------------------------------------------------------------
    # MACD Signal
    # -------------------------------------------------------------------------
    "macd": {
        "signals": {
            "bullish_cross": {
                "zone": "bullish_cross",
                "zone_en": "Bullish Crossover",
                "zone_ru": "Бычье пересечение",
                "explanation_en": "MACD crossed above signal line. Momentum is shifting bullish.",
                "explanation_ru": "MACD пересёк сигнальную линию снизу вверх. Импульс становится бычьим.",
                "action_en": "Consider long positions or adding to existing",
                "action_ru": "Рассмотрите длинные позиции или добавление к существующим",
                "severity": "opportunity",
            },
            "bearish_cross": {
                "zone": "bearish_cross",
                "zone_en": "Bearish Crossover",
                "zone_ru": "Медвежье пересечение",
                "explanation_en": "MACD crossed below signal line. Momentum is shifting bearish.",
                "explanation_ru": "MACD пересёк сигнальную линию сверху вниз. Импульс становится медвежьим.",
                "action_en": "Consider reducing positions or hedging",
                "action_ru": "Рассмотрите сокращение позиций или хеджирование",
                "severity": "warning",
            },
            "bullish_divergence": {
                "zone": "bullish_divergence",
                "zone_en": "Bullish Divergence",
                "zone_ru": "Бычья дивергенция",
                "explanation_en": "Price making lower lows but MACD making higher lows. Potential reversal up.",
                "explanation_ru": "Цена делает более низкие минимумы, но MACD - более высокие. Потенциальный разворот вверх.",
                "action_en": "Watch for confirmation - potential bottom",
                "action_ru": "Следите за подтверждением - возможное дно",
                "severity": "opportunity",
            },
            "bearish_divergence": {
                "zone": "bearish_divergence",
                "zone_en": "Bearish Divergence",
                "zone_ru": "Медвежья дивергенция",
                "explanation_en": "Price making higher highs but MACD making lower highs. Potential reversal down.",
                "explanation_ru": "Цена делает более высокие максимумы, но MACD - более низкие. Потенциальный разворот вниз.",
                "action_en": "Consider taking profits - momentum weakening",
                "action_ru": "Рассмотрите фиксацию прибыли - импульс ослабевает",
                "severity": "warning",
            },
            "neutral": {
                "zone": "neutral",
                "zone_en": "Neutral",
                "zone_ru": "Нейтральный",
                "explanation_en": "No significant MACD signal. Trend continuation expected.",
                "explanation_ru": "Нет значимого сигнала MACD. Ожидается продолжение тренда.",
                "action_en": "Hold current positions",
                "action_ru": "Держите текущие позиции",
                "severity": "info",
            },
        },
    },
    # -------------------------------------------------------------------------
    # Bollinger Bands Position
    # -------------------------------------------------------------------------
    "bollinger_bands": {
        "ranges": [
            {
                "min": -100,
                "max": 0,
                "zone": "below_lower",
                "zone_en": "Below Lower Band",
                "zone_ru": "Ниже нижней полосы",
                "explanation_en": "Price is below the lower Bollinger Band. Oversold or strong downtrend.",
                "explanation_ru": "Цена ниже нижней полосы Боллинджера. Перепроданность или сильный нисходящий тренд.",
                "action_en": "Watch for reversal - potential bounce",
                "action_ru": "Следите за разворотом - возможен отскок",
                "severity": "opportunity",
            },
            {
                "min": 0,
                "max": 25,
                "zone": "lower_zone",
                "zone_en": "Lower Zone",
                "zone_ru": "Нижняя зона",
                "explanation_en": "Price near lower band. May bounce or continue down.",
                "explanation_ru": "Цена возле нижней полосы. Может отскочить или продолжить падение.",
                "action_en": "Look for support and reversal signals",
                "action_ru": "Ищите поддержку и сигналы разворота",
                "severity": "info",
            },
            {
                "min": 25,
                "max": 75,
                "zone": "middle_zone",
                "zone_en": "Middle Zone",
                "zone_ru": "Средняя зона",
                "explanation_en": "Price in the middle of Bollinger Bands. Normal trading range.",
                "explanation_ru": "Цена в середине полос Боллинджера. Нормальный торговый диапазон.",
                "action_en": "Follow trend direction",
                "action_ru": "Следуйте направлению тренда",
                "severity": "info",
            },
            {
                "min": 75,
                "max": 100,
                "zone": "upper_zone",
                "zone_en": "Upper Zone",
                "zone_ru": "Верхняя зона",
                "explanation_en": "Price near upper band. May pull back or continue up.",
                "explanation_ru": "Цена возле верхней полосы. Может откатиться или продолжить рост.",
                "action_en": "Watch for resistance and reversal",
                "action_ru": "Следите за сопротивлением и разворотом",
                "severity": "warning",
            },
            {
                "min": 100,
                "max": 200,
                "zone": "above_upper",
                "zone_en": "Above Upper Band",
                "zone_ru": "Выше верхней полосы",
                "explanation_en": "Price is above the upper Bollinger Band. Overbought or strong uptrend.",
                "explanation_ru": "Цена выше верхней полосы Боллинджера. Перекупленность или сильный восходящий тренд.",
                "action_en": "Consider taking profits - overextended",
                "action_ru": "Рассмотрите фиксацию прибыли - перерастяжение",
                "severity": "warning",
            },
        ],
    },
    # -------------------------------------------------------------------------
    # Trend
    # -------------------------------------------------------------------------
    "trend": {
        "signals": {
            "strong_uptrend": {
                "zone": "strong_uptrend",
                "zone_en": "Strong Uptrend",
                "zone_ru": "Сильный восходящий тренд",
                "explanation_en": "Price is in a strong uptrend. Momentum is bullish.",
                "explanation_ru": "Цена в сильном восходящем тренде. Импульс бычий.",
                "action_en": "Hold longs - trend is your friend",
                "action_ru": "Держите лонги - тренд ваш друг",
                "severity": "info",
            },
            "uptrend": {
                "zone": "uptrend",
                "zone_en": "Uptrend",
                "zone_ru": "Восходящий тренд",
                "explanation_en": "Price is trending up. Bullish bias.",
                "explanation_ru": "Цена в восходящем тренде. Бычий уклон.",
                "action_en": "Look for pullbacks to add",
                "action_ru": "Ищите откаты для добавления",
                "severity": "info",
            },
            "sideways": {
                "zone": "sideways",
                "zone_en": "Sideways",
                "zone_ru": "Боковик",
                "explanation_en": "Price is consolidating. No clear trend direction.",
                "explanation_ru": "Цена консолидируется. Нет чёткого направления тренда.",
                "action_en": "Wait for breakout - trade the range",
                "action_ru": "Ждите пробоя - торгуйте диапазон",
                "severity": "info",
            },
            "downtrend": {
                "zone": "downtrend",
                "zone_en": "Downtrend",
                "zone_ru": "Нисходящий тренд",
                "explanation_en": "Price is trending down. Bearish bias.",
                "explanation_ru": "Цена в нисходящем тренде. Медвежий уклон.",
                "action_en": "Avoid longs - wait for reversal",
                "action_ru": "Избегайте лонгов - ждите разворота",
                "severity": "warning",
            },
            "strong_downtrend": {
                "zone": "strong_downtrend",
                "zone_en": "Strong Downtrend",
                "zone_ru": "Сильный нисходящий тренд",
                "explanation_en": "Price is in a strong downtrend. High risk for longs.",
                "explanation_ru": "Цена в сильном нисходящем тренде. Высокий риск для лонгов.",
                "action_en": "Stay out or short only - danger zone",
                "action_ru": "Оставайтесь в стороне или только шорт - зона опасности",
                "severity": "danger",
            },
        },
    },
    # -------------------------------------------------------------------------
    # Sharpe Ratio
    # -------------------------------------------------------------------------
    "sharpe_ratio": {
        "ranges": [
            {
                "min": -100,
                "max": 0,
                "zone": "negative",
                "zone_en": "Negative",
                "zone_ru": "Отрицательный",
                "explanation_en": "Negative Sharpe ratio means returns are worse than risk-free rate.",
                "explanation_ru": "Отрицательный коэффициент Шарпа означает, что доходность хуже безрисковой ставки.",
                "action_en": "Review and rebalance portfolio",
                "action_ru": "Пересмотрите и ребалансируйте портфель",
                "severity": "danger",
            },
            {
                "min": 0,
                "max": 1,
                "zone": "poor",
                "zone_en": "Poor",
                "zone_ru": "Плохой",
                "explanation_en": "Low risk-adjusted returns. Portfolio may need optimization.",
                "explanation_ru": "Низкая доходность с поправкой на риск. Портфель может нуждаться в оптимизации.",
                "action_en": "Consider diversification or strategy review",
                "action_ru": "Рассмотрите диверсификацию или пересмотр стратегии",
                "severity": "warning",
            },
            {
                "min": 1,
                "max": 2,
                "zone": "good",
                "zone_en": "Good",
                "zone_ru": "Хороший",
                "explanation_en": "Good risk-adjusted returns. Portfolio is performing well.",
                "explanation_ru": "Хорошая доходность с поправкой на риск. Портфель работает хорошо.",
                "action_en": "Maintain current strategy",
                "action_ru": "Поддерживайте текущую стратегию",
                "severity": "info",
            },
            {
                "min": 2,
                "max": 3,
                "zone": "very_good",
                "zone_en": "Very Good",
                "zone_ru": "Очень хороший",
                "explanation_en": "Excellent risk-adjusted returns. Strong performance.",
                "explanation_ru": "Отличная доходность с поправкой на риск. Сильные результаты.",
                "action_en": "Keep doing what you're doing",
                "action_ru": "Продолжайте в том же духе",
                "severity": "info",
            },
            {
                "min": 3,
                "max": 100,
                "zone": "excellent",
                "zone_en": "Excellent",
                "zone_ru": "Отличный",
                "explanation_en": "Outstanding risk-adjusted returns. Top-tier performance.",
                "explanation_ru": "Выдающаяся доходность с поправкой на риск. Высший уровень.",
                "action_en": "Excellent! Monitor for sustainability",
                "action_ru": "Отлично! Следите за устойчивостью",
                "severity": "opportunity",
            },
        ],
    },
    # -------------------------------------------------------------------------
    # Drawdown
    # -------------------------------------------------------------------------
    "drawdown": {
        "ranges": [
            {
                "min": 0,
                "max": 5,
                "zone": "minimal",
                "zone_en": "Minimal",
                "zone_ru": "Минимальная",
                "explanation_en": "Very small drawdown. Portfolio is near its highs.",
                "explanation_ru": "Очень маленькая просадка. Портфель близок к максимумам.",
                "action_en": "Good position - continue monitoring",
                "action_ru": "Хорошая позиция - продолжайте мониторинг",
                "severity": "info",
            },
            {
                "min": 5,
                "max": 10,
                "zone": "normal",
                "zone_en": "Normal",
                "zone_ru": "Нормальная",
                "explanation_en": "Normal market fluctuation. Within acceptable range.",
                "explanation_ru": "Нормальные рыночные колебания. В допустимом диапазоне.",
                "action_en": "Hold steady - normal volatility",
                "action_ru": "Держитесь - нормальная волатильность",
                "severity": "info",
            },
            {
                "min": 10,
                "max": 20,
                "zone": "elevated",
                "zone_en": "Elevated",
                "zone_ru": "Повышенная",
                "explanation_en": "Significant drawdown. Monitor closely.",
                "explanation_ru": "Значительная просадка. Внимательно следите.",
                "action_en": "Review risk management",
                "action_ru": "Пересмотрите управление рисками",
                "severity": "warning",
            },
            {
                "min": 20,
                "max": 30,
                "zone": "high",
                "zone_en": "High",
                "zone_ru": "Высокая",
                "explanation_en": "High drawdown. Consider risk reduction.",
                "explanation_ru": "Высокая просадка. Рассмотрите снижение риска.",
                "action_en": "Reduce position sizes or hedge",
                "action_ru": "Уменьшите размер позиций или хеджируйте",
                "severity": "danger",
            },
            {
                "min": 30,
                "max": 100,
                "zone": "severe",
                "zone_en": "Severe",
                "zone_ru": "Серьёзная",
                "explanation_en": "Severe drawdown. Major losses. Review entire strategy.",
                "explanation_ru": "Серьёзная просадка. Крупные убытки. Пересмотрите всю стратегию.",
                "action_en": "Urgent: reassess risk tolerance and strategy",
                "action_ru": "Срочно: переоцените толерантность к риску и стратегию",
                "severity": "danger",
            },
        ],
    },
    # -------------------------------------------------------------------------
    # Funding Rate
    # -------------------------------------------------------------------------
    "funding_rate": {
        "ranges": [
            {
                "min": -1,
                "max": -0.03,
                "zone": "very_negative",
                "zone_en": "Very Negative",
                "zone_ru": "Очень отрицательный",
                "explanation_en": "Shorts are paying longs heavily. Strong bullish signal.",
                "explanation_ru": "Шорты сильно платят лонгам. Сильный бычий сигнал.",
                "action_en": "Consider long positions - shorts overextended",
                "action_ru": "Рассмотрите лонги - шорты перегружены",
                "severity": "opportunity",
            },
            {
                "min": -0.03,
                "max": -0.01,
                "zone": "negative",
                "zone_en": "Negative",
                "zone_ru": "Отрицательный",
                "explanation_en": "Shorts paying longs. Bullish bias.",
                "explanation_ru": "Шорты платят лонгам. Бычий уклон.",
                "action_en": "Favorable for longs",
                "action_ru": "Благоприятно для лонгов",
                "severity": "opportunity",
            },
            {
                "min": -0.01,
                "max": 0.01,
                "zone": "neutral",
                "zone_en": "Neutral",
                "zone_ru": "Нейтральный",
                "explanation_en": "Balanced funding. No strong bias from derivatives.",
                "explanation_ru": "Сбалансированный фандинг. Нет сильного уклона от деривативов.",
                "action_en": "Normal market conditions",
                "action_ru": "Нормальные рыночные условия",
                "severity": "info",
            },
            {
                "min": 0.01,
                "max": 0.05,
                "zone": "positive",
                "zone_en": "Positive",
                "zone_ru": "Положительный",
                "explanation_en": "Longs paying shorts. Bullish sentiment but watch for overheating.",
                "explanation_ru": "Лонги платят шортам. Бычье настроение, но следите за перегревом.",
                "action_en": "Be cautious with new longs",
                "action_ru": "Будьте осторожны с новыми лонгами",
                "severity": "warning",
            },
            {
                "min": 0.05,
                "max": 1,
                "zone": "very_positive",
                "zone_en": "Very Positive",
                "zone_ru": "Очень положительный",
                "explanation_en": "Longs are paying shorts heavily. Market overheated.",
                "explanation_ru": "Лонги сильно платят шортам. Рынок перегрет.",
                "action_en": "Avoid longs - correction likely",
                "action_ru": "Избегайте лонгов - вероятна коррекция",
                "severity": "danger",
            },
        ],
    },
    # -------------------------------------------------------------------------
    # Volatility
    # -------------------------------------------------------------------------
    "volatility": {
        "ranges": [
            {
                "min": 0,
                "max": 20,
                "zone": "low",
                "zone_en": "Low",
                "zone_ru": "Низкая",
                "explanation_en": "Low volatility. Calm market. Big move may be brewing.",
                "explanation_ru": "Низкая волатильность. Спокойный рынок. Возможно назревает большое движение.",
                "action_en": "Prepare for potential breakout",
                "action_ru": "Готовьтесь к возможному пробою",
                "severity": "info",
            },
            {
                "min": 20,
                "max": 40,
                "zone": "normal",
                "zone_en": "Normal",
                "zone_ru": "Нормальная",
                "explanation_en": "Normal volatility levels. Standard trading conditions.",
                "explanation_ru": "Нормальные уровни волатильности. Стандартные торговые условия.",
                "action_en": "Business as usual",
                "action_ru": "Работа в обычном режиме",
                "severity": "info",
            },
            {
                "min": 40,
                "max": 60,
                "zone": "elevated",
                "zone_en": "Elevated",
                "zone_ru": "Повышенная",
                "explanation_en": "Elevated volatility. Expect larger price swings.",
                "explanation_ru": "Повышенная волатильность. Ожидайте больших колебаний цены.",
                "action_en": "Reduce position sizes or widen stops",
                "action_ru": "Уменьшите размер позиций или расширьте стопы",
                "severity": "warning",
            },
            {
                "min": 60,
                "max": 80,
                "zone": "high",
                "zone_en": "High",
                "zone_ru": "Высокая",
                "explanation_en": "High volatility. Significant risk of large moves.",
                "explanation_ru": "Высокая волатильность. Значительный риск крупных движений.",
                "action_en": "Trade cautiously - high risk",
                "action_ru": "Торгуйте осторожно - высокий риск",
                "severity": "warning",
            },
            {
                "min": 80,
                "max": 200,
                "zone": "extreme",
                "zone_en": "Extreme",
                "zone_ru": "Экстремальная",
                "explanation_en": "Extreme volatility. Very dangerous market conditions.",
                "explanation_ru": "Экстремальная волатильность. Очень опасные рыночные условия.",
                "action_en": "Consider staying out - extreme risk",
                "action_ru": "Рассмотрите выход - экстремальный риск",
                "severity": "danger",
            },
        ],
    },
}


# =============================================================================
# Explanation Service
# =============================================================================


class ExplanationService:
    """
    Provides human-readable explanations for metrics.

    All explanations are bilingual (English + Russian).
    """

    def get_explanation(self, metric: str, value: float, lang: str = "en") -> MetricExplanation | None:
        """
        Get explanation for a metric value.

        Args:
            metric: Metric name (e.g., "rsi", "fear_greed")
            value: Current value of the metric
            lang: Language ("en" or "ru")

        Returns:
            MetricExplanation with zone, explanation, and action
        """
        if metric not in EXPLANATIONS:
            logger.warning(f"No explanations found for metric: {metric}")
            return None

        metric_data = EXPLANATIONS[metric]

        # Handle range-based metrics
        if "ranges" in metric_data:
            for range_def in metric_data["ranges"]:
                if range_def["min"] <= value < range_def["max"]:
                    return MetricExplanation(
                        zone=range_def["zone"],
                        zone_en=range_def["zone_en"],
                        zone_ru=range_def["zone_ru"],
                        explanation=range_def[f"explanation_{lang}"],
                        explanation_ru=range_def["explanation_ru"],
                        action=range_def[f"action_{lang}"],
                        action_ru=range_def["action_ru"],
                        severity=range_def["severity"],
                    )

        return None

    def get_signal_explanation(self, metric: str, signal: str, lang: str = "en") -> MetricExplanation | None:
        """
        Get explanation for a signal-based metric.

        Args:
            metric: Metric name (e.g., "macd", "trend")
            signal: Signal name (e.g., "bullish_cross", "uptrend")
            lang: Language ("en" or "ru")
        """
        if metric not in EXPLANATIONS:
            return None

        metric_data = EXPLANATIONS[metric]

        if "signals" in metric_data and signal in metric_data["signals"]:
            signal_def = metric_data["signals"][signal]
            return MetricExplanation(
                zone=signal_def["zone"],
                zone_en=signal_def["zone_en"],
                zone_ru=signal_def["zone_ru"],
                explanation=signal_def[f"explanation_{lang}"],
                explanation_ru=signal_def["explanation_ru"],
                action=signal_def[f"action_{lang}"],
                action_ru=signal_def["action_ru"],
                severity=signal_def["severity"],
            )

        return None

    def get_all_explanations(self, metrics: dict, lang: str = "en") -> dict:
        """
        Get explanations for multiple metrics at once.

        Args:
            metrics: Dict of {metric_name: value}
            lang: Language preference

        Returns:
            Dict of {metric_name: MetricExplanation}
        """
        result = {}
        for metric, value in metrics.items():
            if isinstance(value, (int, float)):
                explanation = self.get_explanation(metric, value, lang)
            else:
                explanation = self.get_signal_explanation(metric, str(value), lang)

            if explanation:
                result[metric] = explanation

        return result

    def format_sensor_attributes(self, metric: str, value: float | str) -> dict:
        """
        Format explanation as sensor attributes for Home Assistant.

        Returns dict with bilingual attributes ready for MQTT publish.
        """
        if isinstance(value, (int, float)):
            explanation = self.get_explanation(metric, value)
        else:
            explanation = self.get_signal_explanation(metric, str(value))

        if not explanation:
            return {}

        return {
            "zone": explanation.zone,
            "zone_en": explanation.zone_en,
            "zone_ru": explanation.zone_ru,
            "explanation": explanation.explanation,
            "explanation_ru": explanation.explanation_ru,
            "action": explanation.action,
            "action_ru": explanation.action_ru,
            "severity": explanation.severity,
        }
