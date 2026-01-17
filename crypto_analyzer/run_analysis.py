#!/usr/bin/env python3
"""
Run Analysis - Главная точка входа для Crypto Analyzer

Использование:
    python run_analysis.py                    # Полный анализ всех монет
    python run_analysis.py --symbol BTC       # Анализ конкретной монеты
    python run_analysis.py --update           # Обновить данные и анализ
    python run_analysis.py --backfill         # Начальная загрузка данных
    python run_analysis.py --json             # Вывод в JSON (для HA)
    python run_analysis.py --summary          # Краткая сводка
    python run_analysis.py --full             # Полный анализ (включая options, news, macro)
    python run_analysis.py --arbitrage        # Сканирование арбитража
    python run_analysis.py --defi             # DeFi yields
    python run_analysis.py --macro            # Макро анализ

Примеры для Home Assistant:
    shell_command:
      crypto_update: "python3 /config/_tools/crypto_analyzer/run_analysis.py --update --json"
      crypto_analyze: "python3 /config/_tools/crypto_analyzer/run_analysis.py --symbol BTC --json"
      crypto_full: "python3 /config/_tools/crypto_analyzer/run_analysis.py --full --json"
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from analysis import TechnicalAnalyzer
from arbitrage import ArbitrageScanner
from collector import DataCollector
from cycles import CycleDetector
from database import get_database
from defi_tracker import DeFiTracker
from derivatives import DerivativesAnalyzer
from macro import MacroAnalyzer
from mtf_analysis import MTFAnalyzer
from news_parser import NewsParser
from onchain import OnChainAnalyzer
from options_flow import OptionsFlowAnalyzer
from patterns import PatternDetector

# Новые модули (Фазы 4-6)
from scoring import ScoringEngine
from sentiment import SentimentAnalyzer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Список монет по умолчанию
DEFAULT_COINS = ["BTC", "ETH", "SOL", "ADA", "XRP", "DOT"]


class CryptoAnalyzerRunner:
    """Главный класс для запуска анализа"""

    def __init__(self):
        self.db = get_database()
        self.ta = TechnicalAnalyzer(self.db)
        self.mtf = MTFAnalyzer(self.db)
        self.patterns = PatternDetector(self.db)
        self.cycles = CycleDetector(self.db)
        self.scoring = ScoringEngine(self.db)

        # Async analyzers (инициализируем по требованию)
        self._onchain = None
        self._derivatives = None
        self._sentiment = None
        self._options = None
        self._news = None
        self._arbitrage = None
        self._defi = None
        self._macro = None

    async def _get_onchain(self) -> OnChainAnalyzer:
        if self._onchain is None:
            self._onchain = OnChainAnalyzer(self.db)
        return self._onchain

    async def _get_derivatives(self) -> DerivativesAnalyzer:
        if self._derivatives is None:
            self._derivatives = DerivativesAnalyzer(self.db)
        return self._derivatives

    async def _get_sentiment(self) -> SentimentAnalyzer:
        if self._sentiment is None:
            self._sentiment = SentimentAnalyzer(self.db)
        return self._sentiment

    async def _get_options(self) -> OptionsFlowAnalyzer:
        if self._options is None:
            self._options = OptionsFlowAnalyzer(self.db)
        return self._options

    async def _get_news(self) -> NewsParser:
        if self._news is None:
            self._news = NewsParser(self.db)
        return self._news

    async def _get_arbitrage(self) -> ArbitrageScanner:
        if self._arbitrage is None:
            self._arbitrage = ArbitrageScanner(self.db)
        return self._arbitrage

    async def _get_defi(self) -> DeFiTracker:
        if self._defi is None:
            self._defi = DeFiTracker(self.db)
        return self._defi

    async def _get_macro(self) -> MacroAnalyzer:
        if self._macro is None:
            self._macro = MacroAnalyzer(self.db)
        return self._macro

    async def close_all(self):
        """Закрыть все async ресурсы"""
        if self._onchain:
            await self._onchain.close()
        if self._derivatives:
            await self._derivatives.close()
        if self._sentiment:
            await self._sentiment.close()
        if self._options:
            await self._options.close()
        if self._news:
            await self._news.close()
        if self._arbitrage:
            await self._arbitrage.close()
        if self._defi:
            await self._defi.close()
        if self._macro:
            await self._macro.close()

    async def update_data(self, symbols: list[str] = None, timeframes: list[str] = None) -> dict:
        """
        Обновить данные из API

        Args:
            symbols: Список символов
            timeframes: Список таймфреймов

        Returns:
            Результат обновления
        """
        symbols = symbols or DEFAULT_COINS
        timeframes = timeframes or ["4h", "1d", "1w"]

        collector = DataCollector(self.db)

        try:
            results = await collector.update_all(symbols, timeframes)

            return {
                "status": "success",
                "updated_candles": sum(results.values()),
                "details": results,
                "timestamp": datetime.now().isoformat(),
            }
        finally:
            await collector.close()

    async def backfill_data(self, symbols: list[str] = None, years: int = 5) -> dict:
        """
        Начальная загрузка исторических данных

        Args:
            symbols: Список символов
            years: Количество лет истории

        Returns:
            Результат загрузки
        """
        symbols = symbols or ["BTC", "ETH", "SOL"]

        years_map = {"BTC": 10, "ETH": 8, "default": years}

        collector = DataCollector(self.db)

        try:
            results = await collector.backfill_all(
                symbols=symbols, timeframes=["1d", "1w"], years_map=years_map
            )

            return {
                "status": "success",
                "total_candles": sum(results.values()),
                "details": results,
                "timestamp": datetime.now().isoformat(),
            }
        finally:
            await collector.close()

    def analyze_symbol(self, symbol: str) -> dict:
        """
        Полный анализ одной монеты

        Args:
            symbol: Символ монеты

        Returns:
            Результат анализа
        """
        # MTF анализ
        mtf_analysis = self.mtf.analyze(symbol)
        mtf_summary = self.mtf.get_summary(symbol)

        # Детальный технический анализ (Daily)
        ta_result = self.ta.analyze_full(symbol, "1d")

        # Паттерны
        detected_patterns = self.patterns.detect_all(symbol)
        patterns_data = [p.to_dict() for p in detected_patterns]

        # Рыночный цикл (только для BTC, остальные коррелируют)
        cycle_info = None
        if symbol.upper() == "BTC":
            cycle = self.cycles.detect_cycle("BTC")
            cycle_info = cycle.to_dict()

        return {
            "symbol": symbol.upper(),
            "timestamp": datetime.now().isoformat(),
            "price": mtf_analysis.price,
            # MTF confluence
            "mtf": {
                "confluence_score": mtf_analysis.confluence_score,
                "confluence_signal": mtf_analysis.confluence_signal_ru,
                "has_divergence": mtf_analysis.has_divergence,
                "divergence": mtf_analysis.divergence_description,
            },
            # Timeframes summary
            "timeframes": mtf_summary.get("timeframes", {}),
            # Technical analysis
            "technical": {
                "rsi": ta_result.get("indicators", {}).get("rsi"),
                "macd_histogram": ta_result.get("indicators", {}).get("macd_histogram"),
                "bb_position": ta_result.get("indicators", {}).get("bb_position"),
                "sma_200": ta_result.get("indicators", {}).get("sma_200"),
                "price_vs_sma200": self._calc_price_vs_sma(
                    mtf_analysis.price, ta_result.get("indicators", {}).get("sma_200")
                ),
            },
            # Patterns (Фаза 2)
            "patterns": {
                "detected": patterns_data,
                "count": len(patterns_data),
                "bullish_count": len([p for p in detected_patterns if p.direction == "bullish"]),
                "bearish_count": len([p for p in detected_patterns if p.direction == "bearish"]),
            },
            # Market Cycle (только для BTC)
            "cycle": cycle_info,
            # Signals
            "signals": ta_result.get("signals", {}),
            # Support/Resistance
            "levels": ta_result.get("support_resistance", {}),
            # Key levels from all TFs
            "key_levels": mtf_analysis.key_levels,
            # Recommendation
            "recommendation": mtf_summary.get("recommendation_ru", ""),
        }

    def _calc_price_vs_sma(self, price: float, sma: float | None) -> float | None:
        """Рассчитать % отклонения от SMA"""
        if not price or not sma:
            return None
        return round(((price - sma) / sma) * 100, 2)

    def analyze_all(self, symbols: list[str] = None) -> dict:
        """
        Анализ всех монет

        Args:
            symbols: Список символов

        Returns:
            Результаты анализа
        """
        symbols = symbols or DEFAULT_COINS

        results = {
            "timestamp": datetime.now().isoformat(),
            "coins": {},
            "summary": {
                "bullish": [],
                "bearish": [],
                "neutral": [],
            },
        }

        for symbol in symbols:
            try:
                analysis = self.analyze_symbol(symbol)
                results["coins"][symbol] = analysis

                # Категоризация
                score = analysis["mtf"]["confluence_score"]
                if score >= 60:
                    results["summary"]["bullish"].append(symbol)
                elif score <= 40:
                    results["summary"]["bearish"].append(symbol)
                else:
                    results["summary"]["neutral"].append(symbol)

            except Exception as e:
                logger.error(f"Ошибка анализа {symbol}: {e}")
                results["coins"][symbol] = {"error": str(e)}

        return results

    def get_market_summary(self, symbols: list[str] = None) -> dict:
        """
        Получить краткую сводку рынка

        Returns:
            Сводка для уведомлений
        """
        analysis = self.analyze_all(symbols)

        # Формируем текстовую сводку
        bullish = analysis["summary"]["bullish"]
        bearish = analysis["summary"]["bearish"]
        neutral = analysis["summary"]["neutral"]

        text_parts = [
            "📊 **Crypto Market Summary**",
            f"_{datetime.now().strftime('%Y-%m-%d %H:%M')}_",
            "",
        ]

        # Cycle info (BTC)
        btc_data = analysis["coins"].get("BTC", {})
        if btc_data.get("cycle"):
            cycle = btc_data["cycle"]
            text_parts.append(f"🔄 **Цикл BTC:** {cycle.get('phase_name_ru', 'N/A')}")
            if cycle.get("halving", {}).get("days_since"):
                text_parts.append(f"   📅 {cycle['halving']['days_since']} дней после халвинга")
            text_parts.append("")

        if bullish:
            text_parts.append(f"🟢 **Бычьи:** {', '.join(bullish)}")
        if bearish:
            text_parts.append(f"🔴 **Медвежьи:** {', '.join(bearish)}")
        if neutral:
            text_parts.append(f"⚪ **Нейтральные:** {', '.join(neutral)}")

        text_parts.append("")

        # Добавляем детали по топ монетам
        for symbol in ["BTC", "ETH"]:
            if symbol in analysis["coins"]:
                coin = analysis["coins"][symbol]
                if "error" not in coin:
                    price = coin.get("price", 0)
                    mtf_score = coin.get("mtf", {}).get("confluence_score", 0)
                    rsi = coin.get("technical", {}).get("rsi", 0)

                    text_parts.append(
                        f"**{symbol}**: ${price:,.0f} | "
                        f"MTF: {mtf_score:.0f}/100 | "
                        f"RSI: {rsi:.0f if rsi else 'N/A'}"
                    )

        text_parts.append("")

        # Паттерны
        all_patterns = []
        for symbol, coin_data in analysis["coins"].items():
            if "patterns" in coin_data and coin_data["patterns"].get("detected"):
                for p in coin_data["patterns"]["detected"]:
                    all_patterns.append(
                        {
                            "symbol": symbol,
                            "name": p.get("name_ru", p.get("name")),
                            "direction": p.get("direction"),
                        }
                    )

        if all_patterns:
            text_parts.append("**📈 Активные паттерны:**")
            for p in all_patterns[:5]:  # Топ 5
                emoji = (
                    "🟢"
                    if p["direction"] == "bullish"
                    else "🔴"
                    if p["direction"] == "bearish"
                    else "⚪"
                )
                text_parts.append(f"  {emoji} {p['symbol']}: {p['name']}")

        return {
            "timestamp": analysis["timestamp"],
            "summary": analysis["summary"],
            "text": "\n".join(text_parts),
            "coins": analysis["coins"],
            "patterns_count": len(all_patterns),
            "cycle": btc_data.get("cycle"),
        }

    def get_ha_sensors_data(self, symbols: list[str] = None) -> dict:
        """
        Получить данные для Home Assistant сенсоров

        Returns:
            Данные в формате для HA
        """
        analysis = self.analyze_all(symbols)

        sensors = {}

        for symbol, data in analysis["coins"].items():
            if "error" in data:
                continue

            prefix = f"crypto_{symbol.lower()}"

            sensors[f"{prefix}_price"] = data.get("price", 0)
            sensors[f"{prefix}_mtf_score"] = data.get("mtf", {}).get("confluence_score", 50)
            sensors[f"{prefix}_mtf_signal"] = data.get("mtf", {}).get(
                "confluence_signal", "unknown"
            )
            sensors[f"{prefix}_rsi"] = data.get("technical", {}).get("rsi", 0)
            sensors[f"{prefix}_recommendation"] = data.get("recommendation", "")

            # Patterns
            patterns = data.get("patterns", {})
            sensors[f"{prefix}_patterns_count"] = patterns.get("count", 0)
            sensors[f"{prefix}_patterns_bullish"] = patterns.get("bullish_count", 0)
            sensors[f"{prefix}_patterns_bearish"] = patterns.get("bearish_count", 0)

            # Timeframes
            for tf, tf_data in data.get("timeframes", {}).items():
                sensors[f"{prefix}_{tf}_trend"] = tf_data.get("trend", "unknown")

        # Cycle info (только BTC)
        btc_cycle = analysis["coins"].get("BTC", {}).get("cycle")
        if btc_cycle:
            sensors["crypto_btc_cycle_phase"] = btc_cycle.get("phase", "unknown")
            sensors["crypto_btc_cycle_phase_ru"] = btc_cycle.get("phase_name_ru", "Неизвестно")
            sensors["crypto_btc_cycle_confidence"] = btc_cycle.get("confidence", 0)
            sensors["crypto_btc_cycle_position"] = btc_cycle.get("cycle_position", 50)
            sensors["crypto_btc_risk_level"] = btc_cycle.get("risk_level", "medium")

            halving = btc_cycle.get("halving", {})
            sensors["crypto_btc_days_since_halving"] = halving.get("days_since", 0)
            sensors["crypto_btc_days_to_halving"] = halving.get("days_to_next", 0)

            price_info = btc_cycle.get("price", {})
            sensors["crypto_btc_from_ath_pct"] = price_info.get("from_ath_pct", 0)
            sensors["crypto_btc_from_atl_pct"] = price_info.get("from_atl_pct", 0)

        return {"timestamp": analysis["timestamp"], "sensors": sensors, "raw": analysis}

    async def analyze_full(self, symbols: list[str] = None) -> dict:
        """
        Полный анализ включая все модули

        Args:
            symbols: Список символов

        Returns:
            Полные результаты анализа
        """
        symbols = symbols or DEFAULT_COINS

        result = {
            "timestamp": datetime.now().isoformat(),
            "analysis": self.analyze_all(symbols),
        }

        try:
            # Sentiment
            sentiment = await self._get_sentiment()
            result["sentiment"] = (await sentiment.analyze()).to_dict()

            # Derivatives для основных монет
            derivatives = await self._get_derivatives()
            result["derivatives"] = {}
            for symbol in ["BTC", "ETH"]:
                if symbol in symbols:
                    deriv_data = await derivatives.analyze(symbol)
                    result["derivatives"][symbol] = deriv_data.to_dict()

            # Options (только BTC/ETH)
            options = await self._get_options()
            result["options"] = {}
            for symbol in ["BTC", "ETH"]:
                if symbol in symbols:
                    opt_data = await options.analyze(symbol)
                    result["options"][symbol] = opt_data.to_dict()

            # On-chain
            onchain = await self._get_onchain()
            result["onchain"] = (await onchain.analyze()).to_dict()

            # Macro
            macro = await self._get_macro()
            result["macro"] = (await macro.analyze()).to_dict()

            # Scoring для каждой монеты
            result["scores"] = {}
            for symbol in symbols:
                score_data = self.scoring.calculate_score(symbol)
                result["scores"][symbol] = score_data

        except Exception as e:
            logger.error(f"Ошибка в full analysis: {e}")
            result["error"] = str(e)

        return result

    async def scan_arbitrage(self, symbols: list[str] = None) -> dict:
        """
        Сканирование арбитражных возможностей

        Args:
            symbols: Список символов

        Returns:
            Результаты сканирования
        """
        arbitrage = await self._get_arbitrage()
        scan = await arbitrage.scan_all(symbols)

        return {
            "timestamp": datetime.now().isoformat(),
            "scan": scan.to_dict(),
            "summary_ru": scan.get_summary_ru(),
        }

    async def get_defi_yields(self, chains: list[str] = None) -> dict:
        """
        Получить лучшие DeFi yields

        Args:
            chains: Фильтр по чейнам

        Returns:
            DeFi данные
        """
        defi = await self._get_defi()
        summary = await defi.get_summary(chains)

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": summary.to_dict(),
            "summary_ru": summary.get_summary_ru(),
        }

    async def get_macro_analysis(self) -> dict:
        """
        Получить макро анализ

        Returns:
            Макро данные
        """
        macro = await self._get_macro()
        analysis = await macro.analyze()

        return {
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis.to_dict(),
            "summary_ru": analysis.get_summary_ru(),
        }

    async def get_news_feed(self, currencies: list[str] = None) -> dict:
        """
        Получить ленту новостей

        Args:
            currencies: Фильтр по валютам

        Returns:
            Новости
        """
        news = await self._get_news()
        feed = await news.get_news_feed(currencies)

        return {
            "timestamp": datetime.now().isoformat(),
            "feed": feed.to_dict(),
            "summary_ru": feed.get_summary_ru(),
        }


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="Crypto Analyzer")

    parser.add_argument("--symbol", "-s", type=str, help="Анализ конкретной монеты")
    parser.add_argument("--symbols", type=str, help="Список монет через запятую")
    parser.add_argument("--update", "-u", action="store_true", help="Обновить данные")
    parser.add_argument("--backfill", "-b", action="store_true", help="Загрузить историю")
    parser.add_argument("--years", type=int, default=5, help="Лет истории для backfill")
    parser.add_argument("--json", "-j", action="store_true", help="Вывод в JSON")
    parser.add_argument("--summary", action="store_true", help="Краткая сводка")
    parser.add_argument("--ha", action="store_true", help="Формат для Home Assistant")
    parser.add_argument("--quiet", "-q", action="store_true", help="Минимальный вывод")

    # Новые команды
    parser.add_argument("--full", "-f", action="store_true", help="Полный анализ (все модули)")
    parser.add_argument("--arbitrage", action="store_true", help="Сканирование арбитража")
    parser.add_argument("--defi", action="store_true", help="DeFi yields")
    parser.add_argument("--macro", action="store_true", help="Макро анализ")
    parser.add_argument("--news", action="store_true", help="Новости")
    parser.add_argument("--chains", type=str, help="Чейны для DeFi (через запятую)")

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    runner = CryptoAnalyzerRunner()

    # Определяем список символов
    symbols = None
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    elif args.symbol:
        symbols = [args.symbol.upper()]

    # Чейны для DeFi
    chains = None
    if args.chains:
        chains = [c.strip() for c in args.chains.split(",")]

    result = {}

    try:
        # Backfill
        if args.backfill:
            logger.info("Запуск backfill...")
            result = await runner.backfill_data(symbols, args.years)

        # Update
        elif args.update:
            logger.info("Обновление данных...")
            result = await runner.update_data(symbols)

            # После обновления - анализ
            if not args.symbol:
                analysis = runner.analyze_all(symbols)
                result["analysis"] = analysis
            else:
                result["analysis"] = runner.analyze_symbol(args.symbol)

        # Full analysis (все модули)
        elif args.full:
            logger.info("Полный анализ...")
            result = await runner.analyze_full(symbols)

        # Arbitrage scan
        elif args.arbitrage:
            logger.info("Сканирование арбитража...")
            result = await runner.scan_arbitrage(symbols)

        # DeFi yields
        elif args.defi:
            logger.info("Получение DeFi данных...")
            result = await runner.get_defi_yields(chains)

        # Macro analysis
        elif args.macro:
            logger.info("Макро анализ...")
            result = await runner.get_macro_analysis()

        # News
        elif args.news:
            logger.info("Получение новостей...")
            result = await runner.get_news_feed(symbols)

        # Summary
        elif args.summary:
            result = runner.get_market_summary(symbols)

        # HA format
        elif args.ha:
            result = runner.get_ha_sensors_data(symbols)

        # Single symbol
        elif args.symbol:
            result = runner.analyze_symbol(args.symbol)

        # All symbols
        else:
            result = runner.analyze_all(symbols)

        # Вывод
        if args.json or args.ha:
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            # Человекочитаемый вывод
            if args.summary:
                print(result.get("text", ""))
            elif any([args.arbitrage, args.defi, args.macro, args.news]):
                # Для новых команд выводим summary_ru если есть
                if "summary_ru" in result:
                    print(result["summary_ru"])
                else:
                    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            else:
                print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)
    finally:
        # Закрываем все ресурсы
        await runner.close_all()


if __name__ == "__main__":
    asyncio.run(main())
