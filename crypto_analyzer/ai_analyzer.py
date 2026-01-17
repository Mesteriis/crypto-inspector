"""
AI Analyzer - Интеграция с Ollama для анализа

Функции:
- Интерпретация технических паттернов
- Сравнение с историческими ситуациями
- Генерация рекомендаций на русском языке
- Объяснение рыночной ситуации
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from config_loader import get_config
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


# Ollama API defaults (переопределяются из config)
DEFAULT_OLLAMA_URL = "http://192.168.1.2:11434"
DEFAULT_MODEL = "llama3.2"


@dataclass
class AIAnalysis:
    """Результат AI анализа"""

    symbol: str
    timestamp: int

    # Интерпретация
    interpretation: str = ""
    interpretation_short: str = ""

    # Рекомендации
    recommendations: list[str] = None

    # Риски
    risks: list[str] = None

    # Ключевые уровни
    key_levels_analysis: str = ""

    # Общий вердикт
    verdict: str = ""
    sentiment: str = "neutral"  # 'bullish', 'bearish', 'neutral'

    # Метаданные
    model_used: str = ""
    tokens_used: int = 0

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []
        if self.risks is None:
            self.risks = []

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "interpretation": self.interpretation,
            "interpretation_short": self.interpretation_short,
            "recommendations": self.recommendations,
            "risks": self.risks,
            "key_levels": self.key_levels_analysis,
            "verdict": self.verdict,
            "sentiment": self.sentiment,
            "meta": {
                "model": self.model_used,
                "tokens": self.tokens_used,
            },
        }


class AIAnalyzer:
    """AI анализатор на базе Ollama"""

    SYSTEM_PROMPT = """Ты опытный криптовалютный аналитик. Отвечай на русском языке.
Будь кратким, конкретным и практичным. Избегай общих фраз.
Всегда указывай конкретные уровни цен, проценты и временные рамки.
Формат ответа: markdown с эмодзи для визуализации."""

    def __init__(self, ollama_url: str = None, model: str = None, db: CryptoDatabase | None = None):
        # Загружаем конфиг
        config = get_config()

        # Ollama URL и модель из config или defaults
        self.ollama_url = (ollama_url or config.get_ollama_url() or DEFAULT_OLLAMA_URL).rstrip("/")
        self.model = model or config.get_ollama_model() or DEFAULT_MODEL

        self.db = db or get_database()
        self._session: aiohttp.ClientSession | None = None

        logger.info(f"AI Analyzer initialized: {self.ollama_url} with model {self.model}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=120)  # 2 минуты для AI
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Закрыть сессию"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _call_ollama(self, prompt: str, system: str = None) -> str | None:
        """
        Вызвать Ollama API

        Args:
            prompt: Запрос
            system: Системный промпт

        Returns:
            Ответ модели или None
        """
        session = await self._get_session()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        if system:
            payload["system"] = system

        try:
            url = f"{self.ollama_url}/api/generate"

            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollama API error: {response.status} - {error_text}")
                    return None

                data = await response.json()
                return data.get("response", "")

        except TimeoutError:
            logger.error("Ollama request timeout")
            return None
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None

    async def check_availability(self) -> bool:
        """Проверить доступность Ollama"""
        session = await self._get_session()

        try:
            url = f"{self.ollama_url}/api/tags"
            async with session.get(url) as response:
                return response.status == 200
        except Exception:
            return False

    async def analyze_market_situation(self, symbol: str, data: dict) -> AIAnalysis:
        """
        Анализ рыночной ситуации с помощью AI

        Args:
            symbol: Символ монеты
            data: Данные анализа (из run_analysis)

        Returns:
            AIAnalysis
        """
        result = AIAnalysis(
            symbol=symbol.upper(),
            timestamp=int(datetime.now().timestamp() * 1000),
            model_used=self.model,
        )

        # Проверяем доступность
        if not await self.check_availability():
            result.interpretation = "AI анализ недоступен (Ollama не отвечает)"
            return result

        # Формируем контекст
        context = self._build_context(symbol, data)

        # Запрос на интерпретацию
        prompt = f"""Проанализируй текущую ситуацию по {symbol}:

{context}

Дай краткий анализ (3-5 предложений):
1. Текущее состояние рынка
2. Ключевые сигналы (бычьи/медвежьи)
3. Вероятный сценарий на ближайшую неделю

Формат: краткий markdown без заголовков."""

        interpretation = await self._call_ollama(prompt, self.SYSTEM_PROMPT)

        if interpretation:
            result.interpretation = interpretation.strip()
            result.interpretation_short = (
                interpretation[:200].strip() + "..."
                if len(interpretation) > 200
                else interpretation.strip()
            )

        # Запрос на рекомендации
        rec_prompt = f"""На основе анализа {symbol}:

{context}

Дай 3 конкретные рекомендации для трейдера.
Формат: простой список без нумерации, каждая с новой строки."""

        recommendations = await self._call_ollama(rec_prompt, self.SYSTEM_PROMPT)

        if recommendations:
            result.recommendations = [
                r.strip().lstrip("•-*")
                for r in recommendations.strip().split("\n")
                if r.strip() and len(r.strip()) > 10
            ][:5]

        # Запрос на риски
        risk_prompt = f"""Какие основные риски для {symbol} сейчас?

{context}

Перечисли 2-3 главных риска. Кратко, по одному предложению каждый."""

        risks = await self._call_ollama(risk_prompt, self.SYSTEM_PROMPT)

        if risks:
            result.risks = [
                r.strip().lstrip("•-*")
                for r in risks.strip().split("\n")
                if r.strip() and len(r.strip()) > 10
            ][:3]

        # Определяем sentiment
        if result.interpretation:
            text_lower = result.interpretation.lower()
            bullish_words = ["бычий", "рост", "покупк", "накоплен", "позитив", "восходящ"]
            bearish_words = ["медвежий", "падени", "продаж", "негатив", "нисходящ", "коррекц"]

            bullish_score = sum(1 for w in bullish_words if w in text_lower)
            bearish_score = sum(1 for w in bearish_words if w in text_lower)

            if bullish_score > bearish_score + 1:
                result.sentiment = "bullish"
            elif bearish_score > bullish_score + 1:
                result.sentiment = "bearish"
            else:
                result.sentiment = "neutral"

        # Вердикт
        verdict_prompt = f"""Одним предложением: стоит ли покупать {symbol} сейчас и почему?

Контекст: MTF Score {data.get('mtf', {}).get('confluence_score', 'N/A')}/100,
RSI {data.get('technical', {}).get('rsi', 'N/A')}"""

        verdict = await self._call_ollama(verdict_prompt, self.SYSTEM_PROMPT)
        if verdict:
            result.verdict = verdict.strip()

        return result

    def _build_context(self, symbol: str, data: dict) -> str:
        """Построить контекст для AI"""
        parts = []

        # Цена
        price = data.get("price")
        if price:
            parts.append(f"Цена: ${price:,.0f}")

        # MTF
        mtf = data.get("mtf", {})
        if mtf:
            parts.append(
                f"MTF Confluence Score: {mtf.get('confluence_score', 'N/A')}/100 ({mtf.get('confluence_signal', 'N/A')})"
            )
            if mtf.get("has_divergence"):
                parts.append(f"⚠️ MTF Divergence: {mtf.get('divergence', '')}")

        # Technical
        tech = data.get("technical", {})
        if tech:
            rsi = tech.get("rsi")
            if rsi:
                rsi_status = "перепродан" if rsi < 30 else "перекуплен" if rsi > 70 else "нейтрален"
                parts.append(f"RSI: {rsi:.0f} ({rsi_status})")

            sma200 = tech.get("price_vs_sma200")
            if sma200 is not None:
                parts.append(f"Цена vs SMA200: {sma200:+.1f}%")

        # Patterns
        patterns = data.get("patterns", {})
        if patterns.get("count", 0) > 0:
            detected = patterns.get("detected", [])
            pattern_names = [p.get("name_ru", p.get("name", "")) for p in detected[:3]]
            parts.append(f"Паттерны: {', '.join(pattern_names)}")

        # Cycle (только для BTC)
        cycle = data.get("cycle")
        if cycle:
            parts.append(f"Фаза цикла: {cycle.get('phase_name_ru', 'N/A')}")
            if cycle.get("halving", {}).get("days_since"):
                parts.append(f"Дней после халвинга: {cycle['halving']['days_since']}")

        # Signals
        signals = data.get("signals", {})
        if signals:
            parts.append(
                f"Общий сигнал: {signals.get('overall_ru', 'N/A')} (score: {signals.get('score', 'N/A')})"
            )

        return "\n".join(parts)

    async def explain_pattern(self, pattern_name: str, pattern_data: dict) -> str:
        """
        Объяснить паттерн простым языком

        Args:
            pattern_name: Название паттерна
            pattern_data: Данные паттерна

        Returns:
            Объяснение на русском
        """
        prompt = f"""Объясни простым языком паттерн "{pattern_name}" в криптовалютах.

Данные паттерна:
- Направление: {pattern_data.get('direction', 'N/A')}
- Сила: {pattern_data.get('strength', 'N/A')}/10
- Последний раз был: {pattern_data.get('last_occurrence', {}).get('days_ago', 'N/A')} дней назад
- Win rate: {pattern_data.get('statistics', {}).get('win_rate', 'N/A')}%

Ответь в 2-3 предложениях: что это значит и как реагировать."""

        return await self._call_ollama(prompt, self.SYSTEM_PROMPT) or f"Паттерн {pattern_name}"

    async def generate_weekly_report(self, coins_data: dict[str, dict]) -> str:
        """
        Сгенерировать еженедельный отчёт

        Args:
            coins_data: Данные по монетам {symbol: analysis_data}

        Returns:
            Отчёт в markdown
        """
        # Формируем контекст
        context_parts = []

        for symbol, data in coins_data.items():
            mtf = data.get("mtf", {})
            tech = data.get("technical", {})

            context_parts.append(f"""
**{symbol}**: ${data.get('price', 0):,.0f}
- MTF Score: {mtf.get('confluence_score', 'N/A')}/100
- RSI: {tech.get('rsi', 'N/A')}
- Сигнал: {mtf.get('confluence_signal', 'N/A')}""")

        context = "\n".join(context_parts)

        prompt = f"""Составь краткий еженедельный отчёт по криптовалютам.

Данные:
{context}

Структура отчёта:
1. 📊 Обзор рынка (2-3 предложения)
2. 🟢 Лучшие возможности
3. ⚠️ Риски недели
4. 💡 Рекомендация

Формат: markdown с эмодзи."""

        report = await self._call_ollama(prompt, self.SYSTEM_PROMPT)

        if not report:
            return "Не удалось сгенерировать отчёт"

        return f"""# 📊 Еженедельный крипто-отчёт
_{datetime.now().strftime('%d.%m.%Y')}_

{report}

---
_Сгенерировано AI ({self.model})_"""


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        analyzer = AIAnalyzer()

        try:
            # Проверяем доступность
            available = await analyzer.check_availability()
            print(f"Ollama доступен: {available}")

            if not available:
                print("Ollama недоступен, выход")
                return

            # Тестовые данные
            test_data = {
                "price": 95000,
                "mtf": {
                    "confluence_score": 65,
                    "confluence_signal": "🟢🟢 Бычий",
                    "has_divergence": False,
                },
                "technical": {
                    "rsi": 58,
                    "price_vs_sma200": 15.5,
                },
                "patterns": {"count": 1, "detected": [{"name_ru": "Golden Cross"}]},
                "cycle": {"phase_name_ru": "Ранний бычий рынок", "halving": {"days_since": 270}},
                "signals": {"overall_ru": "Бычий", "score": 65},
            }

            print("\n" + "=" * 60)
            print("AI ANALYSIS: BTC")
            print("=" * 60)

            result = await analyzer.analyze_market_situation("BTC", test_data)

            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

            print("\n" + "=" * 60)
            print("INTERPRETATION:")
            print("=" * 60)
            print(result.interpretation)

            print("\n" + "=" * 60)
            print("RECOMMENDATIONS:")
            print("=" * 60)
            for rec in result.recommendations:
                print(f"• {rec}")

            print("\n" + "=" * 60)
            print("RISKS:")
            print("=" * 60)
            for risk in result.risks:
                print(f"⚠️ {risk}")

            print("\n" + "=" * 60)
            print(f"VERDICT: {result.verdict}")
            print(f"SENTIMENT: {result.sentiment}")
            print("=" * 60)

        finally:
            await analyzer.close()

    asyncio.run(main())
