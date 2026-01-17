"""
Options Flow - Отслеживание крупных опционов

Источники:
- Deribit API (основной для BTC/ETH опционов)
- CoinGlass (агрегатор)

Функции:
- Put/Call Ratio
- Max Pain calculation
- Open Interest по страйкам
- Unusual Activity detection
- Expiry calendar
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


# API Endpoints
DERIBIT_URL = "https://www.deribit.com/api/v2/public"


@dataclass
class OptionsExpiry:
    """Данные по экспирации"""

    expiry_date: str
    days_to_expiry: int

    calls_oi: float = 0.0  # Open Interest calls
    puts_oi: float = 0.0  # Open Interest puts

    max_pain: float = 0.0  # Max Pain strike

    # Top strikes by OI
    top_call_strikes: list[dict] = field(default_factory=list)
    top_put_strikes: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "expiry_date": self.expiry_date,
            "days_to_expiry": self.days_to_expiry,
            "calls_oi": self.calls_oi,
            "puts_oi": self.puts_oi,
            "put_call_ratio": round(self.puts_oi / self.calls_oi, 3) if self.calls_oi > 0 else 0,
            "max_pain": self.max_pain,
            "top_call_strikes": self.top_call_strikes[:5],
            "top_put_strikes": self.top_put_strikes[:5],
        }


@dataclass
class OptionsData:
    """Полные данные по опционам"""

    symbol: str
    timestamp: int

    # Текущая цена базового актива
    index_price: float = 0.0

    # Общие метрики
    total_calls_oi: float = 0.0
    total_puts_oi: float = 0.0
    put_call_ratio: float = 1.0

    # Max Pain (ближайшая экспирация)
    max_pain: float = 0.0
    max_pain_distance_pct: float = 0.0  # Расстояние до max pain в %

    # Экспирации
    expiries: list[OptionsExpiry] = field(default_factory=list)

    # Unusual activity
    unusual_activity: list[dict] = field(default_factory=list)

    # Сигнал
    signal: str = "neutral"
    signal_ru: str = "Нейтрально"

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "index_price": self.index_price,
            "metrics": {
                "total_calls_oi": self.total_calls_oi,
                "total_puts_oi": self.total_puts_oi,
                "put_call_ratio": round(self.put_call_ratio, 3),
                "max_pain": self.max_pain,
                "max_pain_distance_pct": round(self.max_pain_distance_pct, 2),
            },
            "signal": self.signal,
            "signal_ru": self.signal_ru,
            "nearest_expiry": self.expiries[0].to_dict() if self.expiries else None,
            "expiry_calendar": [e.to_dict() for e in self.expiries[:5]],
            "unusual_activity": self.unusual_activity[:10],
        }

    def get_summary_ru(self) -> str:
        """Резюме на русском"""
        parts = [
            f"📊 **Options Flow: {self.symbol}**",
            f"💰 Индексная цена: ${self.index_price:,.0f}",
            "",
            f"📈 Call OI: {self.total_calls_oi:,.0f}",
            f"📉 Put OI: {self.total_puts_oi:,.0f}",
            f"📊 Put/Call Ratio: **{self.put_call_ratio:.2f}**",
            "",
            f"🎯 Max Pain: **${self.max_pain:,.0f}**",
        ]

        # Интерпретация max pain
        if self.max_pain_distance_pct > 5:
            parts.append(f"⬆️ Цена на {self.max_pain_distance_pct:.1f}% выше Max Pain")
        elif self.max_pain_distance_pct < -5:
            parts.append(f"⬇️ Цена на {abs(self.max_pain_distance_pct):.1f}% ниже Max Pain")
        else:
            parts.append(f"➡️ Цена близка к Max Pain (±{abs(self.max_pain_distance_pct):.1f}%)")

        # Put/Call интерпретация
        parts.append("")
        if self.put_call_ratio > 1.2:
            parts.append("🐻 Высокий Put/Call - медвежий настрой")
        elif self.put_call_ratio < 0.8:
            parts.append("🐂 Низкий Put/Call - бычий настрой")
        else:
            parts.append("➡️ Нейтральный Put/Call")

        # Ближайшая экспирация
        if self.expiries:
            exp = self.expiries[0]
            parts.extend(
                [
                    "",
                    f"📅 Ближайшая экспирация: **{exp.expiry_date}** ({exp.days_to_expiry} дн.)",
                    f"   Max Pain: ${exp.max_pain:,.0f}",
                ]
            )

        # Unusual activity
        if self.unusual_activity:
            parts.extend(["", "🚨 **Необычная активность:**"])
            for ua in self.unusual_activity[:3]:
                parts.append(f"• {ua.get('description', 'N/A')}")

        return "\n".join(parts)


class OptionsFlowAnalyzer:
    """Анализатор опционного рынка"""

    # Поддерживаемые символы (Deribit)
    SUPPORTED_SYMBOLS = ["BTC", "ETH"]

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

    async def _deribit_request(self, method: str, params: dict = None) -> dict | None:
        """
        Запрос к Deribit API

        Args:
            method: API метод
            params: Параметры запроса

        Returns:
            Ответ API
        """
        session = await self._get_session()

        url = f"{DERIBIT_URL}/{method}"

        try:
            async with session.get(url, params=params or {}) as response:
                if response.status != 200:
                    logger.error(f"Deribit API error: {response.status}")
                    return None

                data = await response.json()

                if "error" in data:
                    logger.error(f"Deribit error: {data['error']}")
                    return None

                return data.get("result")

        except Exception as e:
            logger.error(f"Deribit request error: {e}")
            return None

    async def get_index_price(self, symbol: str) -> float | None:
        """
        Получить индексную цену

        Args:
            symbol: BTC или ETH

        Returns:
            Индексная цена
        """
        result = await self._deribit_request(
            "get_index_price", {"index_name": f"{symbol.lower()}_usd"}
        )

        if result:
            return result.get("index_price")
        return None

    async def get_instruments(self, symbol: str, kind: str = "option") -> list[dict]:
        """
        Получить список инструментов

        Args:
            symbol: BTC или ETH
            kind: Тип (option, future)

        Returns:
            Список инструментов
        """
        result = await self._deribit_request(
            "get_instruments", {"currency": symbol.upper(), "kind": kind, "expired": "false"}
        )

        return result or []

    async def get_book_summary(self, symbol: str) -> list[dict]:
        """
        Получить сводку по книге ордеров для всех опционов

        Args:
            symbol: BTC или ETH

        Returns:
            Список с данными по инструментам
        """
        result = await self._deribit_request(
            "get_book_summary_by_currency", {"currency": symbol.upper(), "kind": "option"}
        )

        return result or []

    def _calculate_max_pain(
        self, options: list[dict], index_price: float
    ) -> tuple[float, dict[float, dict]]:
        """
        Рассчитать Max Pain

        Max Pain - страйк, при котором наибольшее количество опционов
        истекает без ценности (OTM)

        Args:
            options: Список опционов с OI
            index_price: Текущая цена индекса

        Returns:
            (max_pain_strike, strikes_data)
        """
        # Группируем по страйкам
        strikes = defaultdict(lambda: {"calls_oi": 0, "puts_oi": 0})

        for opt in options:
            name = opt.get("instrument_name", "")
            oi = opt.get("open_interest", 0)

            # Парсим имя инструмента (например, BTC-28MAR25-100000-C)
            parts = name.split("-")
            if len(parts) >= 4:
                try:
                    strike = float(parts[2])
                    opt_type = parts[3]  # C or P

                    if opt_type == "C":
                        strikes[strike]["calls_oi"] += oi
                    elif opt_type == "P":
                        strikes[strike]["puts_oi"] += oi
                except (ValueError, IndexError):
                    continue

        if not strikes:
            return 0.0, {}

        # Для каждого страйка считаем total pain (сколько денег потеряют)
        max_pain_strike = 0.0
        min_total_pain = float("inf")

        for strike in strikes.keys():
            total_pain = 0.0

            for s, data in strikes.items():
                if strike > s:
                    # Calls ITM
                    total_pain += data["calls_oi"] * (strike - s)
                else:
                    # Puts ITM
                    total_pain += data["puts_oi"] * (s - strike)

            if total_pain < min_total_pain:
                min_total_pain = total_pain
                max_pain_strike = strike

        return max_pain_strike, dict(strikes)

    def _detect_unusual_activity(
        self, options: list[dict], threshold_oi: float = 1000
    ) -> list[dict]:
        """
        Обнаружить необычную активность

        Args:
            options: Список опционов
            threshold_oi: Порог OI для "необычной" активности

        Returns:
            Список необычных позиций
        """
        unusual = []

        for opt in options:
            oi = opt.get("open_interest", 0)
            volume = opt.get("volume", 0)

            # Необычная активность если:
            # 1. Большой OI
            # 2. Volume > OI * 0.1 (высокая активность)
            if oi > threshold_oi or (volume > 0 and volume > oi * 0.1):
                name = opt.get("instrument_name", "")
                parts = name.split("-")

                if len(parts) >= 4:
                    try:
                        strike = float(parts[2])
                        opt_type = "Call" if parts[3] == "C" else "Put"
                        expiry = parts[1]

                        unusual.append(
                            {
                                "instrument": name,
                                "type": opt_type,
                                "strike": strike,
                                "expiry": expiry,
                                "open_interest": oi,
                                "volume": volume,
                                "description": f"{opt_type} ${strike:,.0f} exp {expiry} - OI: {oi:,.0f}, Vol: {volume:,.0f}",
                            }
                        )
                    except (ValueError, IndexError):
                        continue

        # Сортируем по OI
        unusual.sort(key=lambda x: x["open_interest"], reverse=True)

        return unusual

    async def analyze(self, symbol: str) -> OptionsData:
        """
        Полный анализ опционов

        Args:
            symbol: BTC или ETH

        Returns:
            OptionsData
        """
        symbol = symbol.upper()

        if symbol not in self.SUPPORTED_SYMBOLS:
            logger.warning(f"Options not supported for {symbol}")
            return OptionsData(symbol=symbol, timestamp=int(datetime.now().timestamp() * 1000))

        data = OptionsData(symbol=symbol, timestamp=int(datetime.now().timestamp() * 1000))

        # Получаем данные параллельно
        tasks = [
            self.get_index_price(symbol),
            self.get_book_summary(symbol),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Index price
        index_price = results[0] if not isinstance(results[0], Exception) else None
        if index_price:
            data.index_price = index_price

        # Book summary (все опционы)
        options = results[1] if not isinstance(results[1], Exception) else []

        if not options:
            logger.warning(f"No options data for {symbol}")
            return data

        # Группируем по экспирации
        expiries_data = defaultdict(list)

        for opt in options:
            name = opt.get("instrument_name", "")
            parts = name.split("-")
            if len(parts) >= 4:
                expiry = parts[1]
                expiries_data[expiry].append(opt)

        # Считаем метрики по экспирациям
        expiry_objects = []

        for expiry, opts in expiries_data.items():
            # Парсим дату экспирации
            try:
                exp_date = datetime.strptime(expiry, "%d%b%y")
                days_to_exp = (exp_date - datetime.now()).days
            except ValueError:
                days_to_exp = 0

            # OI по типам
            calls_oi = sum(
                o.get("open_interest", 0)
                for o in opts
                if o.get("instrument_name", "").endswith("-C")
            )
            puts_oi = sum(
                o.get("open_interest", 0)
                for o in opts
                if o.get("instrument_name", "").endswith("-P")
            )

            # Max Pain для этой экспирации
            max_pain, _ = self._calculate_max_pain(opts, data.index_price)

            # Top strikes
            call_strikes = []
            put_strikes = []

            for opt in opts:
                name = opt.get("instrument_name", "")
                oi = opt.get("open_interest", 0)
                parts = name.split("-")

                if len(parts) >= 4 and oi > 0:
                    try:
                        strike = float(parts[2])
                        if parts[3] == "C":
                            call_strikes.append({"strike": strike, "oi": oi})
                        else:
                            put_strikes.append({"strike": strike, "oi": oi})
                    except ValueError:
                        continue

            call_strikes.sort(key=lambda x: x["oi"], reverse=True)
            put_strikes.sort(key=lambda x: x["oi"], reverse=True)

            exp_obj = OptionsExpiry(
                expiry_date=expiry,
                days_to_expiry=days_to_exp,
                calls_oi=calls_oi,
                puts_oi=puts_oi,
                max_pain=max_pain,
                top_call_strikes=call_strikes[:5],
                top_put_strikes=put_strikes[:5],
            )
            expiry_objects.append(exp_obj)

        # Сортируем по дате экспирации
        expiry_objects.sort(key=lambda x: x.days_to_expiry)
        data.expiries = expiry_objects

        # Общие метрики
        data.total_calls_oi = sum(e.calls_oi for e in expiry_objects)
        data.total_puts_oi = sum(e.puts_oi for e in expiry_objects)

        if data.total_calls_oi > 0:
            data.put_call_ratio = data.total_puts_oi / data.total_calls_oi

        # Max Pain (ближайшая экспирация)
        if expiry_objects:
            data.max_pain = expiry_objects[0].max_pain
            if data.index_price > 0 and data.max_pain > 0:
                data.max_pain_distance_pct = (
                    (data.index_price - data.max_pain) / data.max_pain * 100
                )

        # Unusual activity
        data.unusual_activity = self._detect_unusual_activity(options)

        # Определяем сигнал
        data.signal, data.signal_ru = self._get_signal(data)

        return data

    def _get_signal(self, data: OptionsData) -> tuple[str, str]:
        """
        Определить сигнал на основе опционных данных

        Args:
            data: OptionsData

        Returns:
            (signal, signal_ru)
        """
        signals = []

        # Put/Call Ratio
        if data.put_call_ratio > 1.3:
            signals.append(("bearish", "Медвежий", 2))
        elif data.put_call_ratio < 0.7:
            signals.append(("bullish", "Бычий", 2))

        # Max Pain distance
        if data.max_pain_distance_pct > 10:
            signals.append(("bearish", "Медвежий", 1))  # Цена может упасть к max pain
        elif data.max_pain_distance_pct < -10:
            signals.append(("bullish", "Бычий", 1))  # Цена может вырасти к max pain

        if not signals:
            return "neutral", "Нейтрально"

        # Считаем веса
        bullish_weight = sum(w for s, _, w in signals if s == "bullish")
        bearish_weight = sum(w for s, _, w in signals if s == "bearish")

        if bullish_weight > bearish_weight:
            if bullish_weight >= 3:
                return "strong_bullish", "Сильно бычий"
            return "bullish", "Бычий"
        elif bearish_weight > bullish_weight:
            if bearish_weight >= 3:
                return "strong_bearish", "Сильно медвежий"
            return "bearish", "Медвежий"
        else:
            return "neutral", "Нейтрально"


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    async def main():
        analyzer = OptionsFlowAnalyzer()

        try:
            for symbol in ["BTC", "ETH"]:
                print(f"\nAnalyzing {symbol} options...")
                data = await analyzer.analyze(symbol)

                print("\n" + "=" * 60)
                print(f"OPTIONS DATA: {symbol}")
                print("=" * 60)
                print(json.dumps(data.to_dict(), indent=2, ensure_ascii=False))

                print("\n" + "=" * 60)
                print("SUMMARY (RU)")
                print("=" * 60)
                print(data.get_summary_ru())

        finally:
            await analyzer.close()

    asyncio.run(main())
