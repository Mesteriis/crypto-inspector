"""
AI Prompt Templates.

Contains structured prompts for different analysis types:
- Daily market summary
- Weekly analysis report
- Risk assessment
- Trading opportunity analysis
- DCA recommendation
"""

from dataclasses import dataclass


@dataclass
class MarketData:
    """Market data for AI analysis."""

    # Prices
    btc_price: float
    eth_price: float
    btc_change_24h: float
    eth_change_24h: float

    # Indicators
    fear_greed: int
    fear_greed_label: str
    btc_dominance: float
    altseason_index: int

    # Technical
    btc_rsi: float | None = None
    eth_rsi: float | None = None
    btc_trend: str | None = None  # uptrend, downtrend, sideways
    btc_support: float | None = None
    btc_resistance: float | None = None

    # Volatility
    volatility_30d: float | None = None
    volatility_status: str | None = None

    # On-chain
    exchange_flow: str | None = None  # Bullish, Bearish, Neutral
    whale_activity: str | None = None

    # Macro
    next_macro_event: str | None = None
    days_to_fomc: int | None = None

    # Portfolio (optional)
    portfolio_value: float | None = None
    portfolio_pnl_24h: float | None = None

    def to_context(self) -> str:
        """Convert to context string for AI prompt."""
        lines = [
            "=== Current Market Data ===",
            f"BTC Price: ${self.btc_price:,.0f} ({self.btc_change_24h:+.2f}% 24h)",
            f"ETH Price: ${self.eth_price:,.0f} ({self.eth_change_24h:+.2f}% 24h)",
            "",
            "=== Sentiment ===",
            f"Fear & Greed Index: {self.fear_greed} ({self.fear_greed_label})",
            f"BTC Dominance: {self.btc_dominance:.1f}%",
            f"Altseason Index: {self.altseason_index}",
        ]

        if self.btc_rsi is not None:
            lines.extend(
                [
                    "",
                    "=== Technical Analysis ===",
                    f"BTC RSI: {self.btc_rsi:.1f}",
                ]
            )
            if self.eth_rsi:
                lines.append(f"ETH RSI: {self.eth_rsi:.1f}")
            if self.btc_trend:
                lines.append(f"BTC Trend: {self.btc_trend}")
            if self.btc_support and self.btc_resistance:
                lines.append(f"BTC Support/Resistance: ${self.btc_support:,.0f} / ${self.btc_resistance:,.0f}")

        if self.volatility_30d:
            lines.extend(
                [
                    "",
                    "=== Volatility ===",
                    f"30-day Volatility: {self.volatility_30d:.1f}%",
                    f"Status: {self.volatility_status or 'N/A'}",
                ]
            )

        if self.exchange_flow:
            lines.extend(
                [
                    "",
                    "=== On-Chain ===",
                    f"Exchange Flow: {self.exchange_flow}",
                ]
            )
            if self.whale_activity:
                lines.append(f"Whale Activity: {self.whale_activity}")

        if self.next_macro_event:
            lines.extend(
                [
                    "",
                    "=== Macro ===",
                    f"Next Event: {self.next_macro_event}",
                ]
            )
            if self.days_to_fomc is not None:
                lines.append(f"Days to FOMC: {self.days_to_fomc}")

        if self.portfolio_value:
            lines.extend(
                [
                    "",
                    "=== Portfolio ===",
                    f"Value: ${self.portfolio_value:,.2f}",
                    f"24h P&L: {self.portfolio_pnl_24h or 0:+.2f}%",
                ]
            )

        return "\n".join(lines)


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

SYSTEM_PROMPT_ANALYST = """You are an expert cryptocurrency market analyst with deep knowledge of:
- Technical analysis (RSI, MACD, support/resistance, trends)
- On-chain metrics (exchange flows, whale activity)
- Market sentiment (Fear & Greed Index)
- Macroeconomic factors affecting crypto
- Bitcoin halving cycles

Your analysis style:
- Concise and actionable
- Data-driven with specific numbers
- Balanced (mention both bullish and bearish factors)
- Risk-aware (always mention potential risks)
- No financial advice disclaimers needed (user understands this is analysis)

Language: Respond in the same language as the user's request.
"""

SYSTEM_PROMPT_DCA = """You are a DCA (Dollar Cost Averaging) strategy advisor for cryptocurrency investments.

Your expertise:
- DCA timing optimization based on Fear & Greed
- Position sizing based on market conditions
- Risk management for long-term investors

Guidelines:
- Focus on long-term accumulation, not trading
- Consider Fear & Greed for buy timing
- Suggest specific multipliers (e.g., 1.5x normal amount in extreme fear)
- Be conservative with risk
"""

SYSTEM_PROMPT_RISK = """You are a cryptocurrency risk analyst specializing in:
- Portfolio risk assessment
- Volatility analysis
- Downside protection strategies
- Position sizing recommendations

Your analysis includes:
- Value at Risk (VaR) interpretation
- Drawdown analysis
- Correlation risks
- Concentration risks

Be specific with numbers and percentages.
"""


# =============================================================================
# USER PROMPTS
# =============================================================================


def get_daily_summary_prompt(data: MarketData, language: str = "en") -> str:
    """Generate daily market summary prompt."""
    context = data.to_context()

    if language == "ru":
        return f"""Проанализируй текущую рыночную ситуацию и дай краткую сводку.

{context}

Структура ответа:
1. 📊 **Общая картина** (2-3 предложения)
2. 🎯 **Ключевые уровни** для BTC
3. ⚠️ **Риски** на сегодня
4. 💡 **Рекомендация** для долгосрочного инвестора

Будь кратким, максимум 200 слов."""

    return f"""Analyze the current market situation and provide a brief summary.

{context}

Response structure:
1. 📊 **Market Overview** (2-3 sentences)
2. 🎯 **Key Levels** for BTC
3. ⚠️ **Today's Risks**
4. 💡 **Recommendation** for long-term investor

Be concise, maximum 200 words."""


def get_weekly_report_prompt(data: MarketData, language: str = "en") -> str:
    """Generate weekly analysis report prompt."""
    context = data.to_context()

    if language == "ru":
        return f"""Подготовь еженедельный отчет по крипторынку.

{context}

Структура отчета:
1. 📈 **Итоги недели** - что произошло
2. 🔮 **Прогноз на неделю** - чего ожидать
3. 📊 **Технический анализ BTC**
4. 🌊 **Сезонность** - альтсезон или биткоин-сезон
5. 💰 **DCA план** - рекомендуемая сумма на неделю
6. 🚨 **Риски и события**

Максимум 400 слов."""

    return f"""Prepare a weekly crypto market report.

{context}

Report structure:
1. 📈 **Week Summary** - what happened
2. 🔮 **Week Ahead** - what to expect
3. 📊 **BTC Technical Analysis**
4. 🌊 **Seasonality** - altseason or bitcoin season
5. 💰 **DCA Plan** - recommended amount for the week
6. 🚨 **Risks and Events**

Maximum 400 words."""


def get_opportunity_prompt(symbol: str, data: MarketData, language: str = "en") -> str:
    """Generate trading opportunity analysis prompt."""
    context = data.to_context()

    if language == "ru":
        return f"""Проанализируй возможность для {symbol}.

{context}

Ответь на вопросы:
1. Это хорошее время для покупки {symbol}?
2. Какие ключевые уровни?
3. Какой размер позиции рекомендуешь?
4. Где ставить стоп-лосс?
5. Какие риски?

Краткий ответ, максимум 150 слов."""

    return f"""Analyze the opportunity for {symbol}.

{context}

Answer these questions:
1. Is this a good time to buy {symbol}?
2. What are the key levels?
3. What position size do you recommend?
4. Where to place stop-loss?
5. What are the risks?

Brief answer, maximum 150 words."""


def get_dca_recommendation_prompt(data: MarketData, base_amount: float, language: str = "en") -> str:
    """Generate DCA recommendation prompt."""
    context = data.to_context()

    if language == "ru":
        return f"""Дай рекомендацию по DCA на этой неделе.

{context}

Базовая сумма: €{base_amount}

Ответь:
1. Какой множитель применить? (0.5x, 1x, 1.5x, 2x)
2. Сколько инвестировать?
3. Почему?
4. Лучшее время для покупки?

Краткий ответ в 3-4 предложениях."""

    return f"""Give DCA recommendation for this week.

{context}

Base amount: €{base_amount}

Answer:
1. What multiplier to apply? (0.5x, 1x, 1.5x, 2x)
2. How much to invest?
3. Why?
4. Best time to buy?

Brief answer in 3-4 sentences."""


def get_risk_assessment_prompt(
    data: MarketData,
    portfolio_allocation: dict[str, float] | None = None,
    language: str = "en",
) -> str:
    """Generate risk assessment prompt."""
    context = data.to_context()

    allocation_str = ""
    if portfolio_allocation:
        allocation_str = "\nPortfolio allocation:\n"
        for asset, pct in portfolio_allocation.items():
            allocation_str += f"- {asset}: {pct:.1f}%\n"

    if language == "ru":
        return f"""Оцени текущие риски портфеля.

{context}
{allocation_str}

Оцени:
1. 🔴 **Общий уровень риска** (Low/Medium/High/Critical)
2. ⚠️ **Главные риски** (топ-3)
3. 🛡️ **Рекомендации по защите**
4. 📊 **Нужна ли ребалансировка?**

Краткий ответ."""

    return f"""Assess current portfolio risks.

{context}
{allocation_str}

Evaluate:
1. 🔴 **Overall Risk Level** (Low/Medium/High/Critical)
2. ⚠️ **Main Risks** (top-3)
3. 🛡️ **Protection Recommendations**
4. 📊 **Is rebalancing needed?**

Brief answer."""


def get_market_sentiment_prompt(data: MarketData, language: str = "en") -> str:
    """Generate market sentiment analysis prompt."""
    context = data.to_context()

    if language == "ru":
        return f"""Проанализируй текущий сентимент рынка.

{context}

Одним словом опиши сентимент: Bullish, Bearish, или Neutral.
Затем кратко объясни почему (2-3 предложения)."""

    return f"""Analyze current market sentiment.

{context}

Describe sentiment in one word: Bullish, Bearish, or Neutral.
Then briefly explain why (2-3 sentences)."""


# =============================================================================
# FORMATTING HELPERS
# =============================================================================


def format_ai_response_for_ha(response: str, max_length: int = 255) -> str:
    """
    Format AI response for Home Assistant sensor.

    HA sensors have character limits, so we truncate if needed.
    """
    # Remove excessive whitespace
    response = " ".join(response.split())

    if len(response) <= max_length:
        return response

    # Truncate at last complete sentence within limit
    truncated = response[: max_length - 3]
    last_period = truncated.rfind(".")
    last_exclaim = truncated.rfind("!")
    last_question = truncated.rfind("?")

    last_sentence_end = max(last_period, last_exclaim, last_question)

    if last_sentence_end > max_length // 2:
        return response[: last_sentence_end + 1]

    return truncated + "..."


def extract_sentiment_from_response(response: str) -> str:
    """Extract sentiment label from AI response."""
    response_lower = response.lower()

    if "bullish" in response_lower:
        return "Bullish"
    elif "bearish" in response_lower:
        return "Bearish"
    else:
        return "Neutral"


def extract_recommendation_from_response(response: str) -> str:
    """Extract recommendation type from AI response."""
    response_lower = response.lower()

    buy_keywords = ["buy", "accumulate", "покупать", "накапливать", "dca"]
    sell_keywords = ["sell", "take profit", "продавать", "фиксировать"]
    hold_keywords = ["hold", "wait", "держать", "ждать"]

    for keyword in buy_keywords:
        if keyword in response_lower:
            return "Buy"

    for keyword in sell_keywords:
        if keyword in response_lower:
            return "Sell"

    for keyword in hold_keywords:
        if keyword in response_lower:
            return "Hold"

    return "Neutral"
