"""
Bybit Exchange API Client.

Authenticated client for Bybit V5 API:
- HMAC-SHA256 signature generation
- Unified Account endpoints
- Rate limiting and retry logic

API Documentation: https://bybit-exchange.github.io/docs/v5/intro
"""

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float, handling empty strings and None."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# Bybit API endpoints
BYBIT_MAINNET = "https://api.bybit.com"
BYBIT_TESTNET = "https://api-testnet.bybit.com"

# Rate limiting
MAX_REQUESTS_PER_SECOND = 10
RECV_WINDOW = 5000  # 5 seconds


class AccountType(Enum):
    """Bybit account types."""

    UNIFIED = "UNIFIED"
    CONTRACT = "CONTRACT"
    SPOT = "SPOT"
    FUND = "FUND"


class OrderSide(Enum):
    """Order side."""

    BUY = "Buy"
    SELL = "Sell"


@dataclass
class Balance:
    """Account balance for a single coin."""

    coin: str
    wallet_balance: float
    available_balance: float
    locked_balance: float
    usd_value: float
    unrealized_pnl: float = 0
    cumulative_pnl: float = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "coin": self.coin,
            "wallet_balance": round(self.wallet_balance, 8),
            "available_balance": round(self.available_balance, 8),
            "locked_balance": round(self.locked_balance, 8),
            "usd_value": round(self.usd_value, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "cumulative_pnl": round(self.cumulative_pnl, 2),
        }


@dataclass
class EarnPosition:
    """Bybit Earn position (Flexible Savings / OnChain)."""

    coin: str
    product_id: str
    amount: float
    total_pnl: float
    claimable_yield: float
    category: str  # FlexibleSaving or OnChain
    status: str = "Active"
    estimated_apy: float = 0
    usd_value: float = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "coin": self.coin,
            "product_id": self.product_id,
            "amount": round(self.amount, 8),
            "total_pnl": round(self.total_pnl, 8),
            "claimable_yield": round(self.claimable_yield, 8),
            "category": self.category,
            "category_ru": "Гибкий депозит" if self.category == "FlexibleSaving" else "On-Chain",
            "status": self.status,
            "estimated_apy": round(self.estimated_apy, 2),
            "usd_value": round(self.usd_value, 2),
        }


@dataclass
class Position:
    """Open position."""

    symbol: str
    side: str
    size: float
    entry_price: float
    mark_price: float
    leverage: float
    unrealized_pnl: float
    realized_pnl: float
    liq_price: float | None
    take_profit: float | None
    stop_loss: float | None
    position_value: float
    created_time: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "side_ru": "Лонг" if self.side == "Buy" else "Шорт",
            "size": round(self.size, 8),
            "entry_price": round(self.entry_price, 2),
            "mark_price": round(self.mark_price, 2),
            "leverage": f"{self.leverage}x",
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_emoji": "🟢" if self.unrealized_pnl >= 0 else "🔴",
            "realized_pnl": round(self.realized_pnl, 2),
            "liq_price": round(self.liq_price, 2) if self.liq_price else None,
            "take_profit": round(self.take_profit, 2) if self.take_profit else None,
            "stop_loss": round(self.stop_loss, 2) if self.stop_loss else None,
            "position_value": round(self.position_value, 2),
            "pnl_percent": round(
                (self.unrealized_pnl / self.position_value * 100) if self.position_value > 0 else 0,
                2,
            ),
        }


@dataclass
class Trade:
    """Executed trade."""

    trade_id: str
    order_id: str
    symbol: str
    side: str
    price: float
    qty: float
    value: float
    fee: float
    fee_currency: str
    realized_pnl: float
    exec_time: datetime
    is_maker: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "side_ru": "Покупка" if self.side == "Buy" else "Продажа",
            "price": round(self.price, 2),
            "qty": round(self.qty, 8),
            "value": round(self.value, 2),
            "fee": round(self.fee, 8),
            "fee_currency": self.fee_currency,
            "realized_pnl": round(self.realized_pnl, 2),
            "exec_time": self.exec_time.isoformat(),
            "exec_time_str": self.exec_time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_maker": self.is_maker,
            "type": "Maker" if self.is_maker else "Taker",
        }


@dataclass
class AccountSummary:
    """Account summary."""

    total_equity: float
    total_available: float
    total_margin_used: float
    total_unrealized_pnl: float
    account_type: str
    balances: list[Balance] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    earn_positions: list[EarnPosition] = field(default_factory=list)

    @property
    def total_earn_value(self) -> float:
        """Total value in Earn products."""
        return sum(p.usd_value for p in self.earn_positions)

    @property
    def total_portfolio_value(self) -> float:
        """Total portfolio value including wallet + earn."""
        return self.total_equity + self.total_earn_value

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_equity": round(self.total_equity, 2),
            "total_equity_formatted": self._format_currency(self.total_equity),
            "total_available": round(self.total_available, 2),
            "total_margin_used": round(self.total_margin_used, 2),
            "total_unrealized_pnl": round(self.total_unrealized_pnl, 2),
            "unrealized_pnl_emoji": "🟢" if self.total_unrealized_pnl >= 0 else "🔴",
            "account_type": self.account_type,
            "balances": [b.to_dict() for b in self.balances],
            "balances_count": len(self.balances),
            "positions": [p.to_dict() for p in self.positions],
            "positions_count": len(self.positions),
            # Earn data
            "earn_positions": [e.to_dict() for e in self.earn_positions],
            "earn_positions_count": len(self.earn_positions),
            "total_earn_value": round(self.total_earn_value, 2),
            "total_portfolio_value": round(self.total_portfolio_value, 2),
            "total_portfolio_formatted": self._format_currency(self.total_portfolio_value),
        }

    def _format_currency(self, value: float) -> str:
        if value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if value >= 1_000:
            return f"${value / 1_000:.1f}K"
        return f"${value:.2f}"


class BybitClient:
    """
    Bybit API client with authentication.

    Supports Bybit V5 unified account API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        testnet: bool | None = None,
        timeout: float = 30.0,
    ):
        self._api_key = api_key or settings.BYBIT_API_KEY
        self._api_secret = api_secret or settings.BYBIT_API_SECRET
        self._testnet = testnet if testnet is not None else settings.BYBIT_TESTNET
        self._base_url = BYBIT_TESTNET if self._testnet else BYBIT_MAINNET
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._last_request_time = 0.0

    @property
    def is_configured(self) -> bool:
        """Check if API credentials are configured."""
        return bool(self._api_key and self._api_secret)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _generate_signature(self, timestamp: int, params: str) -> str:
        """Generate HMAC-SHA256 signature for API request."""
        param_str = f"{timestamp}{self._api_key}{RECV_WINDOW}{params}"
        return hmac.new(
            self._api_secret.encode("utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _get_auth_headers(self, params: str = "") -> dict[str, str]:
        """Generate authentication headers."""
        timestamp = int(time.time() * 1000)
        signature = self._generate_signature(timestamp, params)

        return {
            "X-BAPI-API-KEY": self._api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-RECV-WINDOW": str(RECV_WINDOW),
        }

    async def _rate_limit(self) -> None:
        """Apply rate limiting."""
        now = time.time()
        elapsed = now - self._last_request_time
        min_interval = 1.0 / MAX_REQUESTS_PER_SECOND

        if elapsed < min_interval:
            await self._async_sleep(min_interval - elapsed)

        self._last_request_time = time.time()

    async def _async_sleep(self, seconds: float) -> None:
        """Async sleep helper."""
        import asyncio

        await asyncio.sleep(seconds)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        authenticated: bool = True,
    ) -> dict[str, Any]:
        """Make API request."""
        if authenticated and not self.is_configured:
            raise ValueError("Bybit API credentials not configured")

        await self._rate_limit()
        client = await self._get_client()

        # Build sorted query string for signature calculation
        # IMPORTANT: params must be sorted and consistent for signature to match
        if method == "GET" and params:
            # Sort params and convert all values to strings
            sorted_params = sorted((k, str(v)) for k, v in params.items())
            query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        else:
            query_string = ""

        # Add auth headers
        headers = {}
        if authenticated:
            if method == "GET":
                headers = self._get_auth_headers(query_string)
            else:
                import json

                headers = self._get_auth_headers(json.dumps(params) if params else "")

        try:
            if method == "GET":
                # Use the exact same query string for the request
                url = endpoint
                if query_string:
                    url = f"{endpoint}?{query_string}"
                response = await client.get(url, headers=headers)
            else:
                response = await client.post(endpoint, json=params, headers=headers)

            response.raise_for_status()
            data = response.json()

            # Check Bybit response code
            if data.get("retCode") != 0:
                error_msg = data.get("retMsg", "Unknown error")
                logger.error(f"Bybit API error: {error_msg}")
                raise Exception(f"Bybit API error: {error_msg}")

            return data.get("result", {})

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise

    # === Account Endpoints ===

    async def get_wallet_balance(self, account_type: AccountType = AccountType.UNIFIED) -> AccountSummary:
        """
        Get wallet balance.

        Args:
            account_type: Account type (UNIFIED, CONTRACT, SPOT, FUND)

        Returns:
            AccountSummary with balances
        """
        data = await self._request(
            "GET",
            "/v5/account/wallet-balance",
            params={"accountType": account_type.value},
        )

        accounts = data.get("list", [])
        if not accounts:
            return AccountSummary(
                total_equity=0,
                total_available=0,
                total_margin_used=0,
                total_unrealized_pnl=0,
                account_type=account_type.value,
            )

        account = accounts[0]
        balances = []

        for coin_data in account.get("coin", []):
            wallet_bal = _safe_float(coin_data.get("walletBalance"))
            if wallet_bal > 0:
                balances.append(
                    Balance(
                        coin=coin_data.get("coin", ""),
                        wallet_balance=wallet_bal,
                        available_balance=_safe_float(coin_data.get("availableToWithdraw")),
                        locked_balance=_safe_float(coin_data.get("locked")),
                        usd_value=_safe_float(coin_data.get("usdValue")),
                        unrealized_pnl=_safe_float(coin_data.get("unrealisedPnl")),
                        cumulative_pnl=_safe_float(coin_data.get("cumRealisedPnl")),
                    )
                )

        return AccountSummary(
            total_equity=_safe_float(account.get("totalEquity")),
            total_available=_safe_float(account.get("totalAvailableBalance")),
            total_margin_used=_safe_float(account.get("totalMarginBalance"))
            - _safe_float(account.get("totalAvailableBalance")),
            total_unrealized_pnl=_safe_float(account.get("totalPerpUPL")),
            account_type=account_type.value,
            balances=balances,
        )

    async def get_positions(self, category: str = "linear", symbol: str | None = None) -> list[Position]:
        """
        Get open positions.

        Args:
            category: Product type (linear, inverse, option)
            symbol: Optional symbol filter

        Returns:
            List of open positions
        """
        params = {"category": category, "settleCoin": "USDT"}
        if symbol:
            params["symbol"] = symbol

        data = await self._request("GET", "/v5/position/list", params=params)

        positions = []
        for pos_data in data.get("list", []):
            size = _safe_float(pos_data.get("size"))
            if size == 0:
                continue

            liq_price = _safe_float(pos_data.get("liqPrice"))
            take_profit = _safe_float(pos_data.get("takeProfit"))
            stop_loss = _safe_float(pos_data.get("stopLoss"))

            positions.append(
                Position(
                    symbol=pos_data.get("symbol", ""),
                    side=pos_data.get("side", ""),
                    size=size,
                    entry_price=_safe_float(pos_data.get("avgPrice")),
                    mark_price=_safe_float(pos_data.get("markPrice")),
                    leverage=_safe_float(pos_data.get("leverage"), 1.0),
                    unrealized_pnl=_safe_float(pos_data.get("unrealisedPnl")),
                    realized_pnl=_safe_float(pos_data.get("cumRealisedPnl")),
                    liq_price=liq_price or None,
                    take_profit=take_profit or None,
                    stop_loss=stop_loss or None,
                    position_value=_safe_float(pos_data.get("positionValue")),
                    created_time=datetime.fromtimestamp(int(pos_data.get("createdTime", 0)) / 1000)
                    if pos_data.get("createdTime")
                    else None,
                )
            )

        return positions

    async def get_trade_history(
        self,
        category: str = "linear",
        symbol: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[Trade]:
        """
        Get trade/execution history.

        Args:
            category: Product type (linear, inverse, spot)
            symbol: Optional symbol filter
            start_time: Start time filter
            end_time: End time filter
            limit: Max records (default 100, max 100)

        Returns:
            List of trades
        """
        params: dict[str, Any] = {"category": category, "limit": min(limit, 100)}

        if symbol:
            params["symbol"] = symbol
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        data = await self._request("GET", "/v5/execution/list", params=params)

        trades = []
        for trade_data in data.get("list", []):
            trades.append(
                Trade(
                    trade_id=trade_data.get("execId", ""),
                    order_id=trade_data.get("orderId", ""),
                    symbol=trade_data.get("symbol", ""),
                    side=trade_data.get("side", ""),
                    price=_safe_float(trade_data.get("execPrice")),
                    qty=_safe_float(trade_data.get("execQty")),
                    value=_safe_float(trade_data.get("execValue")),
                    fee=_safe_float(trade_data.get("execFee")),
                    fee_currency=trade_data.get("feeCurrency", "USDT"),
                    realized_pnl=_safe_float(trade_data.get("closedPnl")),
                    exec_time=datetime.fromtimestamp(int(trade_data.get("execTime", 0)) / 1000),
                    is_maker=trade_data.get("isMaker", False),
                )
            )

        return trades

    async def get_closed_pnl(
        self,
        category: str = "linear",
        symbol: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get closed P&L records.

        Args:
            category: Product type
            symbol: Optional symbol filter
            start_time: Start time filter
            end_time: End time filter
            limit: Max records

        Returns:
            List of closed P&L records
        """
        params: dict[str, Any] = {"category": category, "limit": min(limit, 100)}

        if symbol:
            params["symbol"] = symbol
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        data = await self._request("GET", "/v5/position/closed-pnl", params=params)

        records = []
        for record in data.get("list", []):
            records.append(
                {
                    "symbol": record.get("symbol", ""),
                    "side": record.get("side", ""),
                    "qty": _safe_float(record.get("qty")),
                    "entry_price": _safe_float(record.get("avgEntryPrice")),
                    "exit_price": _safe_float(record.get("avgExitPrice")),
                    "closed_pnl": _safe_float(record.get("closedPnl")),
                    "created_time": datetime.fromtimestamp(int(record.get("createdTime", 0)) / 1000).isoformat(),
                    "updated_time": datetime.fromtimestamp(int(record.get("updatedTime", 0)) / 1000).isoformat(),
                }
            )

        return records

    # === Market Data (Public) ===

    async def get_ticker(self, symbol: str, category: str = "linear") -> dict[str, Any]:
        """Get ticker for symbol."""
        data = await self._request(
            "GET",
            "/v5/market/tickers",
            params={"category": category, "symbol": symbol},
            authenticated=False,
        )

        tickers = data.get("list", [])
        if tickers:
            ticker = tickers[0]
            return {
                "symbol": ticker.get("symbol"),
                "last_price": _safe_float(ticker.get("lastPrice")),
                "mark_price": _safe_float(ticker.get("markPrice")),
                "index_price": _safe_float(ticker.get("indexPrice")),
                "change_24h": _safe_float(ticker.get("price24hPcnt")) * 100,
                "volume_24h": _safe_float(ticker.get("volume24h")),
                "turnover_24h": _safe_float(ticker.get("turnover24h")),
                "funding_rate": _safe_float(ticker.get("fundingRate")),
                "open_interest": _safe_float(ticker.get("openInterest")),
            }
        return {}

    async def get_tickers(
        self, category: str = "linear", symbols: list[str] | None = None
    ) -> dict[str, dict[str, Any]]:
        """Get tickers for multiple symbols."""
        data = await self._request(
            "GET",
            "/v5/market/tickers",
            params={"category": category},
            authenticated=False,
        )

        result = {}
        for ticker in data.get("list", []):
            sym = ticker.get("symbol", "")
            if symbols and sym not in symbols:
                continue

            result[sym] = {
                "last_price": _safe_float(ticker.get("lastPrice")),
                "mark_price": _safe_float(ticker.get("markPrice")),
                "change_24h": _safe_float(ticker.get("price24hPcnt")) * 100,
                "volume_24h": _safe_float(ticker.get("volume24h")),
                "funding_rate": _safe_float(ticker.get("fundingRate")),
            }

        return result

    # === Earn Endpoints ===

    async def get_earn_products(
        self,
        category: str = "FlexibleSaving",
        coin: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get Earn product info.

        Args:
            category: FlexibleSaving or OnChain
            coin: Optional coin filter

        Returns:
            List of earn products with APY info
        """
        params: dict[str, Any] = {"category": category}
        if coin:
            params["coin"] = coin.upper()

        try:
            data = await self._request(
                "GET",
                "/v5/earn/product",
                params=params,
                authenticated=False,  # Public endpoint
            )

            products = []
            for product in data.get("list", []):
                products.append(
                    {
                        "product_id": product.get("productId", ""),
                        "coin": product.get("coin", ""),
                        "category": product.get("category", ""),
                        "estimated_apy": _safe_float(product.get("estimateApr")) * 100,
                        "min_stake": _safe_float(product.get("minStakeAmount")),
                        "max_stake": _safe_float(product.get("maxStakeAmount")),
                        "status": product.get("status", ""),
                    }
                )
            return products

        except Exception as e:
            logger.error(f"Failed to get earn products: {e}")
            return []

    async def get_earn_positions(
        self,
        category: str = "FlexibleSaving",
        coin: str | None = None,
    ) -> list[EarnPosition]:
        """
        Get Earn staked positions.

        Args:
            category: FlexibleSaving or OnChain
            coin: Optional coin filter

        Returns:
            List of EarnPosition
        """
        if not self.is_configured:
            return []

        params: dict[str, Any] = {"category": category}
        if coin:
            params["coin"] = coin.upper()

        try:
            data = await self._request(
                "GET",
                "/v5/earn/position",
                params=params,
            )

            # Get products for APY info
            products = await self.get_earn_products(category)
            product_apys = {p["product_id"]: p["estimated_apy"] for p in products}

            # Get current prices for USD value
            tickers = await self.get_tickers(category="spot")

            positions = []
            for pos in data.get("list", []):
                amount = _safe_float(pos.get("amount"))
                if amount <= 0:
                    continue

                coin_name = pos.get("coin", "")
                product_id = pos.get("productId", "")

                # Calculate USD value
                usd_value = 0.0
                if coin_name == "USDT" or coin_name == "USDC":
                    usd_value = amount
                else:
                    ticker_symbol = f"{coin_name}USDT"
                    if ticker_symbol in tickers:
                        usd_value = amount * tickers[ticker_symbol]["last_price"]

                positions.append(
                    EarnPosition(
                        coin=coin_name,
                        product_id=product_id,
                        amount=amount,
                        total_pnl=_safe_float(pos.get("totalPnl")),
                        claimable_yield=_safe_float(pos.get("claimableYield")),
                        category=category,
                        status=pos.get("status", "Active"),
                        estimated_apy=product_apys.get(product_id, 0),
                        usd_value=usd_value,
                    )
                )

            return positions

        except Exception as e:
            logger.error(f"Failed to get earn positions: {e}")
            return []

    async def get_all_earn_positions(self) -> list[EarnPosition]:
        """
        Get all Earn positions (both FlexibleSaving and OnChain).

        Returns:
            Combined list of all earn positions
        """
        flexible = await self.get_earn_positions(category="FlexibleSaving")
        onchain = await self.get_earn_positions(category="OnChain")
        return flexible + onchain


# Global instance
_bybit_client: BybitClient | None = None


def get_bybit_client() -> BybitClient:
    """Get global Bybit client instance."""
    global _bybit_client
    if _bybit_client is None:
        _bybit_client = BybitClient()
    return _bybit_client
