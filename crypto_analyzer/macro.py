"""
Macro Correlations - Анализ макро корреляций

Отслеживаемые индексы:
- DXY (US Dollar Index)
- S&P 500
- Gold (XAU)
- US 10Y Treasury Yield

Функции:
- Получение данных макро индексов
- Расчёт корреляций с криптой
- Анализ влияния макро факторов
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


# API Endpoints - публичные источники
# Для production рекомендуется использовать платные API (Alpha Vantage, Yahoo Finance API)
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"


@dataclass
class MacroIndex:
    """Макро индекс"""

    symbol: str
    name: str
    name_ru: str

    # Текущие данные
    price: float = 0.0
    change_1d: float = 0.0
    change_1d_pct: float = 0.0
    change_1w_pct: float = 0.0
    change_1m_pct: float = 0.0

    # Исторические данные (для корреляций)
    price_history: list[float] = field(default_factory=list)

    # Уровни
    high_52w: float = 0.0
    low_52w: float = 0.0

    # Метаданные
    last_update: int = 0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "name_ru": self.name_ru,
            "price": self.price,
            "change_1d": round(self.change_1d, 2),
            "change_1d_pct": round(self.change_1d_pct, 2),
            "change_1w_pct": round(self.change_1w_pct, 2),
            "change_1m_pct": round(self.change_1m_pct, 2),
            "high_52w": self.high_52w,
            "low_52w": self.low_52w,
            "last_update": self.last_update,
        }


@dataclass
class CorrelationData:
    """Данные корреляции"""

    symbol: str
    correlation_30d: float = 0.0
    correlation_90d: float = 0.0
    correlation_1y: float = 0.0

    interpretation: str = ""
    interpretation_ru: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "correlation_30d": round(self.correlation_30d, 3),
            "correlation_90d": round(self.correlation_90d, 3),
            "correlation_1y": round(self.correlation_1y, 3),
            "interpretation": self.interpretation,
            "interpretation_ru": self.interpretation_ru,
        }


@dataclass
class MacroAnalysis:
    """Полный макро анализ"""

    timestamp: int

    # Индексы
    dxy: MacroIndex | None = None
    sp500: MacroIndex | None = None
    gold: MacroIndex | None = None
    us10y: MacroIndex | None = None

    # Корреляции с BTC
    correlations: dict[str, CorrelationData] = field(default_factory=dict)

    # Общий макро sentiment
    macro_sentiment: str = "neutral"  # risk_on, risk_off, neutral
    macro_sentiment_ru: str = "Нейтральный"

    # Рекомендация
    crypto_outlook: str = "neutral"
    crypto_outlook_ru: str = "Нейтральный"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "indices": {
                "dxy": self.dxy.to_dict() if self.dxy else None,
                "sp500": self.sp500.to_dict() if self.sp500 else None,
                "gold": self.gold.to_dict() if self.gold else None,
                "us10y": self.us10y.to_dict() if self.us10y else None,
            },
            "correlations": {k: v.to_dict() for k, v in self.correlations.items()},
            "macro_sentiment": self.macro_sentiment,
            "macro_sentiment_ru": self.macro_sentiment_ru,
            "crypto_outlook": self.crypto_outlook,
            "crypto_outlook_ru": self.crypto_outlook_ru,
        }

    def get_summary_ru(self) -> str:
        """Резюме на русском"""
        parts = [
            "🌍 **Макро Анализ**",
            "",
        ]

        # DXY
        if self.dxy:
            emoji = "🔴" if self.dxy.change_1d_pct > 0 else "🟢"
            parts.append(
                f"{emoji} **DXY** (Индекс доллара): {self.dxy.price:.2f} "
                f"({self.dxy.change_1d_pct:+.2f}%)"
            )

        # S&P 500
        if self.sp500:
            emoji = "🟢" if self.sp500.change_1d_pct > 0 else "🔴"
            parts.append(
                f"{emoji} **S&P 500**: {self.sp500.price:,.0f} "
                f"({self.sp500.change_1d_pct:+.2f}%)"
            )

        # Gold
        if self.gold:
            emoji = "🟡" if self.gold.change_1d_pct > 0 else "⚪"
            parts.append(
                f"{emoji} **Gold**: ${self.gold.price:,.0f} " f"({self.gold.change_1d_pct:+.2f}%)"
            )

        # US10Y
        if self.us10y:
            emoji = "📈" if self.us10y.change_1d_pct > 0 else "📉"
            parts.append(
                f"{emoji} **US 10Y Yield**: {self.us10y.price:.2f}% "
                f"({self.us10y.change_1d_pct:+.2f}%)"
            )

        # Макро sentiment
        parts.extend(
            [
                "",
                f"📊 **Макро фон**: {self.macro_sentiment_ru}",
            ]
        )

        # Интерпретация для крипты
        if self.macro_sentiment == "risk_on":
            parts.append("✅ Risk-On режим - позитивно для крипты")
        elif self.macro_sentiment == "risk_off":
            parts.append("⚠️ Risk-Off режим - негативно для крипты")
        else:
            parts.append("➡️ Нейтральный макро фон")

        # Корреляции
        if self.correlations:
            parts.extend(["", "**Корреляции BTC (30d):**"])
            for symbol, corr in self.correlations.items():
                if corr.correlation_30d != 0:
                    parts.append(f"• {symbol}: {corr.correlation_30d:+.2f}")

        parts.extend(
            [
                "",
                f"🔮 **Прогноз для крипты**: {self.crypto_outlook_ru}",
            ]
        )

        return "\n".join(parts)


class MacroAnalyzer:
    """Анализатор макро корреляций"""

    # Символы для отслеживания (Yahoo Finance)
    MACRO_SYMBOLS = {
        "DXY": {"yahoo": "DX-Y.NYB", "name": "US Dollar Index", "name_ru": "Индекс доллара"},
        "SP500": {"yahoo": "^GSPC", "name": "S&P 500", "name_ru": "S&P 500"},
        "GOLD": {"yahoo": "GC=F", "name": "Gold Futures", "name_ru": "Золото"},
        "US10Y": {"yahoo": "^TNX", "name": "US 10Y Treasury", "name_ru": "Доходность 10Y"},
    }

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Закрыть сессию"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_yahoo_quote(self, symbols: list[str]) -> dict[str, dict]:
        """
        Получить котировки с Yahoo Finance

        Args:
            symbols: Список символов Yahoo

        Returns:
            Данные по символам
        """
        session = await self._get_session()

        try:
            params = {"symbols": ",".join(symbols)}
            headers = {"User-Agent": "Mozilla/5.0"}

            async with session.get(YAHOO_QUOTE_URL, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Yahoo Finance error: {response.status}")
                    return {}

                data = await response.json()

                result = {}
                for quote in data.get("quoteResponse", {}).get("result", []):
                    symbol = quote.get("symbol")
                    result[symbol] = {
                        "price": quote.get("regularMarketPrice", 0),
                        "change": quote.get("regularMarketChange", 0),
                        "change_pct": quote.get("regularMarketChangePercent", 0),
                        "high_52w": quote.get("fiftyTwoWeekHigh", 0),
                        "low_52w": quote.get("fiftyTwoWeekLow", 0),
                    }

                return result

        except Exception as e:
            logger.error(f"Yahoo Finance error: {e}")
            return {}

    async def fetch_index(self, index_key: str) -> MacroIndex | None:
        """
        Получить данные по индексу

        Args:
            index_key: Ключ индекса (DXY, SP500, GOLD, US10Y)

        Returns:
            MacroIndex
        """
        if index_key not in self.MACRO_SYMBOLS:
            return None

        config = self.MACRO_SYMBOLS[index_key]
        yahoo_symbol = config["yahoo"]

        quotes = await self.fetch_yahoo_quote([yahoo_symbol])

        if yahoo_symbol not in quotes:
            return None

        quote = quotes[yahoo_symbol]

        return MacroIndex(
            symbol=index_key,
            name=config["name"],
            name_ru=config["name_ru"],
            price=quote.get("price", 0),
            change_1d=quote.get("change", 0),
            change_1d_pct=quote.get("change_pct", 0),
            high_52w=quote.get("high_52w", 0),
            low_52w=quote.get("low_52w", 0),
            last_update=int(datetime.now().timestamp() * 1000),
        )

    async def fetch_all_indices(self) -> dict[str, MacroIndex]:
        """
        Получить все макро индексы

        Returns:
            Словарь индексов
        """
        yahoo_symbols = [cfg["yahoo"] for cfg in self.MACRO_SYMBOLS.values()]
        quotes = await self.fetch_yahoo_quote(yahoo_symbols)

        indices = {}

        for key, config in self.MACRO_SYMBOLS.items():
            yahoo_symbol = config["yahoo"]

            if yahoo_symbol not in quotes:
                continue

            quote = quotes[yahoo_symbol]

            indices[key] = MacroIndex(
                symbol=key,
                name=config["name"],
                name_ru=config["name_ru"],
                price=quote.get("price", 0),
                change_1d=quote.get("change", 0),
                change_1d_pct=quote.get("change_pct", 0),
                high_52w=quote.get("high_52w", 0),
                low_52w=quote.get("low_52w", 0),
                last_update=int(datetime.now().timestamp() * 1000),
            )

        return indices

    @staticmethod
    def calculate_correlation(series1: list[float], series2: list[float]) -> float:
        """
        Рассчитать корреляцию Пирсона

        Args:
            series1: Первый ряд данных
            series2: Второй ряд данных

        Returns:
            Коэффициент корреляции (-1 to +1)
        """
        if len(series1) != len(series2) or len(series1) < 2:
            return 0.0

        n = len(series1)

        mean1 = sum(series1) / n
        mean2 = sum(series2) / n

        numerator = sum((s1 - mean1) * (s2 - mean2) for s1, s2 in zip(series1, series2))

        var1 = sum((s - mean1) ** 2 for s in series1)
        var2 = sum((s - mean2) ** 2 for s in series2)

        denominator = (var1 * var2) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def _interpret_correlation(self, corr: float, symbol: str) -> tuple[str, str]:
        """
        Интерпретировать корреляцию

        Args:
            corr: Коэффициент корреляции
            symbol: Символ индекса

        Returns:
            (interpretation_en, interpretation_ru)
        """
        abs_corr = abs(corr)

        if abs_corr < 0.3:
            strength = "weak"
            strength_ru = "слабая"
        elif abs_corr < 0.6:
            strength = "moderate"
            strength_ru = "умеренная"
        else:
            strength = "strong"
            strength_ru = "сильная"

        direction = "positive" if corr > 0 else "negative"
        direction_ru = "положительная" if corr > 0 else "отрицательная"

        # Специфичная интерпретация для каждого индекса
        if symbol == "DXY":
            if corr < -0.3:
                return (
                    f"{strength.title()} negative correlation with DXY - crypto rises when dollar falls",
                    f"{strength_ru.title()} {direction_ru} корреляция с долларом - крипта растёт при падении доллара",
                )
            elif corr > 0.3:
                return (
                    f"{strength.title()} positive correlation with DXY - unusual",
                    f"{strength_ru.title()} {direction_ru} корреляция с долларом - необычно",
                )

        elif symbol == "SP500":
            if corr > 0.3:
                return (
                    f"{strength.title()} positive correlation with S&P 500 - follows risk assets",
                    f"{strength_ru.title()} {direction_ru} корреляция с S&P 500 - следует за рисковыми активами",
                )

        elif symbol == "GOLD":
            if corr > 0.3:
                return (
                    f"{strength.title()} positive correlation with Gold - store of value narrative",
                    f"{strength_ru.title()} {direction_ru} корреляция с золотом - нарратив 'цифрового золота'",
                )

        return (
            f"{strength.title()} {direction} correlation",
            f"{strength_ru.title()} {direction_ru} корреляция",
        )

    def _determine_macro_sentiment(self, indices: dict[str, MacroIndex]) -> tuple[str, str]:
        """
        Определить общий макро sentiment

        Risk-On: DXY падает, S&P растёт, доходности падают
        Risk-Off: DXY растёт, S&P падает, доходности растут

        Args:
            indices: Данные по индексам

        Returns:
            (sentiment, sentiment_ru)
        """
        risk_on_signals = 0
        risk_off_signals = 0

        # DXY: падение = risk-on
        dxy = indices.get("DXY")
        if dxy:
            if dxy.change_1d_pct < -0.2:
                risk_on_signals += 1
            elif dxy.change_1d_pct > 0.2:
                risk_off_signals += 1

        # S&P 500: рост = risk-on
        sp500 = indices.get("SP500")
        if sp500:
            if sp500.change_1d_pct > 0.3:
                risk_on_signals += 1
            elif sp500.change_1d_pct < -0.3:
                risk_off_signals += 1

        # US10Y: рост = risk-off (обычно)
        us10y = indices.get("US10Y")
        if us10y:
            if us10y.change_1d_pct > 2:  # Доходности более волатильны
                risk_off_signals += 1
            elif us10y.change_1d_pct < -2:
                risk_on_signals += 1

        # Gold: рост может быть и risk-on (инфляция) и risk-off (хедж)
        # Не учитываем в простой модели

        if risk_on_signals > risk_off_signals:
            return "risk_on", "Risk-On (позитивный)"
        elif risk_off_signals > risk_on_signals:
            return "risk_off", "Risk-Off (негативный)"
        else:
            return "neutral", "Нейтральный"

    def _determine_crypto_outlook(
        self, macro_sentiment: str, correlations: dict[str, CorrelationData]
    ) -> tuple[str, str]:
        """
        Определить прогноз для крипты

        Args:
            macro_sentiment: Макро sentiment
            correlations: Корреляции

        Returns:
            (outlook, outlook_ru)
        """
        if macro_sentiment == "risk_on":
            return "bullish", "Бычий - макро поддерживает рост"
        elif macro_sentiment == "risk_off":
            # Проверяем корреляцию с золотом
            gold_corr = correlations.get("GOLD")
            if gold_corr and gold_corr.correlation_30d > 0.5:
                return "neutral", "Нейтральный - может выступить как хедж"
            return "bearish", "Медвежий - макро давит на риск"
        else:
            return "neutral", "Нейтральный - ждём направления макро"

    async def analyze(self) -> MacroAnalysis:
        """
        Полный макро анализ

        Returns:
            MacroAnalysis
        """
        analysis = MacroAnalysis(timestamp=int(datetime.now().timestamp() * 1000))

        # Получаем все индексы
        indices = await self.fetch_all_indices()

        analysis.dxy = indices.get("DXY")
        analysis.sp500 = indices.get("SP500")
        analysis.gold = indices.get("GOLD")
        analysis.us10y = indices.get("US10Y")

        # Для корреляций нужны исторические данные
        # Placeholder - в реальности нужно собирать историю
        # и считать реальные корреляции

        # Примерные корреляции (для демо)
        analysis.correlations = {
            "DXY": CorrelationData(
                symbol="DXY",
                correlation_30d=-0.45,
                correlation_90d=-0.42,
                correlation_1y=-0.38,
                interpretation="Moderate negative correlation",
                interpretation_ru="Умеренная отрицательная корреляция с долларом",
            ),
            "SP500": CorrelationData(
                symbol="SP500",
                correlation_30d=0.65,
                correlation_90d=0.58,
                correlation_1y=0.52,
                interpretation="Strong positive correlation",
                interpretation_ru="Сильная положительная корреляция с S&P 500",
            ),
            "GOLD": CorrelationData(
                symbol="GOLD",
                correlation_30d=0.35,
                correlation_90d=0.28,
                correlation_1y=0.22,
                interpretation="Weak to moderate positive correlation",
                interpretation_ru="Слабая положительная корреляция с золотом",
            ),
        }

        # Определяем sentiment
        analysis.macro_sentiment, analysis.macro_sentiment_ru = self._determine_macro_sentiment(
            indices
        )

        # Прогноз для крипты
        analysis.crypto_outlook, analysis.crypto_outlook_ru = self._determine_crypto_outlook(
            analysis.macro_sentiment, analysis.correlations
        )

        return analysis


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    async def main():
        analyzer = MacroAnalyzer()

        try:
            print("Analyzing macro correlations...")
            analysis = await analyzer.analyze()

            print("\n" + "=" * 60)
            print("MACRO ANALYSIS")
            print("=" * 60)
            print(json.dumps(analysis.to_dict(), indent=2, ensure_ascii=False))

            print("\n" + "=" * 60)
            print("SUMMARY (RU)")
            print("=" * 60)
            print(analysis.get_summary_ru())

        finally:
            await analyzer.close()

    asyncio.run(main())
