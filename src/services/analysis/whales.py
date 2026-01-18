"""
Whale Activity Tracker.

Monitors large cryptocurrency transactions (whales):
- Track transactions > $1M
- Categorize as exchange inflow/outflow/unknown
- Detect accumulation/distribution patterns

Data sources:
- Whale Alert API (requires API key)
- Blockchain.info for BTC
- Etherscan for ETH
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

# API endpoints
WHALE_ALERT_API = "https://api.whale-alert.io/v1"
BLOCKCHAIN_INFO_API = "https://blockchain.info"


class TransactionType(Enum):
    """Whale transaction type."""

    EXCHANGE_INFLOW = "exchange_inflow"  # To exchange - potential sell
    EXCHANGE_OUTFLOW = "exchange_outflow"  # From exchange - accumulation
    EXCHANGE_TO_EXCHANGE = "exchange_to_exchange"  # Between exchanges
    UNKNOWN = "unknown"  # Wallet to wallet


class WhaleSignal(Enum):
    """Overall whale activity signal."""

    ACCUMULATING = "accumulating"  # More outflows than inflows
    DISTRIBUTING = "distributing"  # More inflows than outflows
    NEUTRAL = "neutral"  # Balanced


@dataclass
class WhaleTransaction:
    """Single whale transaction."""

    timestamp: datetime
    blockchain: str  # bitcoin, ethereum, etc.
    symbol: str  # BTC, ETH, etc.
    amount: float
    amount_usd: float
    tx_type: TransactionType
    from_owner: str | None  # Exchange name or "unknown"
    to_owner: str | None
    tx_hash: str


@dataclass
class WhaleData:
    """Whale activity analysis result."""

    timestamp: datetime
    transactions_24h: int
    total_volume_usd_24h: float
    inflow_count: int
    outflow_count: int
    inflow_volume_usd: float
    outflow_volume_usd: float
    signal: WhaleSignal
    signal_ru: str
    net_flow_usd: float  # Negative = outflow (bullish)
    recent_transactions: list[WhaleTransaction] = field(default_factory=list)
    largest_tx: WhaleTransaction | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API/MQTT."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "transactions_24h": self.transactions_24h,
            "total_volume_usd_24h": self.total_volume_usd_24h,
            "total_volume_formatted": self._format_usd(self.total_volume_usd_24h),
            "inflow_count": self.inflow_count,
            "outflow_count": self.outflow_count,
            "inflow_volume_usd": self.inflow_volume_usd,
            "outflow_volume_usd": self.outflow_volume_usd,
            "net_flow_usd": self.net_flow_usd,
            "net_flow_formatted": self._format_usd(self.net_flow_usd),
            "signal": self.signal.value,
            "signal_ru": self.signal_ru,
            "signal_emoji": self._get_signal_emoji(),
            "recent_transactions": [
                {
                    "time": tx.timestamp.isoformat(),
                    "symbol": tx.symbol,
                    "amount": tx.amount,
                    "amount_usd": tx.amount_usd,
                    "type": tx.tx_type.value,
                    "from": tx.from_owner or "unknown",
                    "to": tx.to_owner or "unknown",
                }
                for tx in self.recent_transactions[:10]
            ],
            "largest_tx": (
                {
                    "symbol": self.largest_tx.symbol,
                    "amount": self.largest_tx.amount,
                    "amount_usd": self.largest_tx.amount_usd,
                    "type": self.largest_tx.tx_type.value,
                }
                if self.largest_tx
                else None
            ),
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _format_usd(self, value: float) -> str:
        """Format USD value."""
        if abs(value) >= 1_000_000_000:
            return f"${value / 1_000_000_000:.1f}B"
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        return f"${value:,.0f}"

    def _get_signal_emoji(self) -> str:
        """Get emoji for signal."""
        if self.signal == WhaleSignal.ACCUMULATING:
            return "🐋🟢"
        if self.signal == WhaleSignal.DISTRIBUTING:
            return "🐋🔴"
        return "🐋⚪"

    def _get_summary(self) -> str:
        """Get English summary."""
        return f"{self.transactions_24h} whale txs (24h), " f"Net flow: {self._format_usd(self.net_flow_usd)}"

    def _get_summary_ru(self) -> str:
        """Get Russian summary."""
        if self.signal == WhaleSignal.ACCUMULATING:
            action = "накапливают"
        elif self.signal == WhaleSignal.DISTRIBUTING:
            action = "распределяют"
        else:
            action = "нейтральны"
        return f"Киты {action}. {self.transactions_24h} транзакций за 24ч"


# Known exchange addresses (simplified list)
KNOWN_EXCHANGES = {
    # Bitcoin exchanges
    "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s": "Binance",
    "3JZq4atUahhuA9rLhXLMhhTo133J9rF97j": "Binance",
    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97": "Bitfinex",
    # Ethereum exchanges
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance",
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503": "Binance Cold",
    "0x742d35cc6634c0532925a3b844bc9e7595f8f22e": "Bitfinex",
}


class WhaleTracker:
    """
    Whale activity tracker.

    Monitors large transactions and categorizes them.
    """

    def __init__(
        self,
        whale_alert_api_key: str | None = None,
        min_value_usd: float = 1_000_000,
        timeout: float = 30.0,
    ):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._whale_alert_key = whale_alert_api_key or os.environ.get("WHALE_ALERT_API_KEY")
        self._min_value = min_value_usd
        self._cached_txs: list[WhaleTransaction] = []
        self._cache_time: datetime | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def analyze(self) -> WhaleData:
        """
        Analyze whale activity over last 24 hours.

        Returns:
            WhaleData with analysis
        """
        client = await self._get_client()

        transactions = []

        # Try Whale Alert API if key available
        if self._whale_alert_key:
            try:
                transactions = await self._fetch_whale_alert(client)
            except Exception as e:
                logger.warning(f"Whale Alert fetch failed: {e}")

        # If no transactions, try simulating from public data
        if not transactions:
            try:
                transactions = await self._fetch_simulated_whales(client)
            except Exception as e:
                logger.warning(f"Simulated whale data failed: {e}")

        # Analyze transactions
        return self._analyze_transactions(transactions)

    async def _fetch_whale_alert(self, client: httpx.AsyncClient) -> list[WhaleTransaction]:
        """Fetch transactions from Whale Alert API."""
        now = datetime.now()
        start_time = int((now - timedelta(hours=24)).timestamp())

        url = f"{WHALE_ALERT_API}/transactions"
        params = {
            "api_key": self._whale_alert_key,
            "min_value": int(self._min_value),
            "start": start_time,
            "limit": 100,
        }

        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("result") != "success":
            raise ValueError(f"Whale Alert error: {data.get('message')}")

        transactions = []
        for tx in data.get("transactions", []):
            tx_type = self._classify_transaction(tx.get("from", {}), tx.get("to", {}))

            transactions.append(
                WhaleTransaction(
                    timestamp=datetime.fromtimestamp(tx.get("timestamp", 0)),
                    blockchain=tx.get("blockchain", "unknown"),
                    symbol=tx.get("symbol", "").upper(),
                    amount=tx.get("amount", 0),
                    amount_usd=tx.get("amount_usd", 0),
                    tx_type=tx_type,
                    from_owner=tx.get("from", {}).get("owner"),
                    to_owner=tx.get("to", {}).get("owner"),
                    tx_hash=tx.get("hash", ""),
                )
            )

        return transactions

    async def _fetch_simulated_whales(self, client: httpx.AsyncClient) -> list[WhaleTransaction]:
        """
        Generate simulated whale data from public APIs.

        This is a fallback when Whale Alert API is not available.
        Uses recent large BTC transactions from blockchain.info.
        """
        # Fetch latest BTC blocks for large transactions
        try:
            response = await client.get(f"{BLOCKCHAIN_INFO_API}/unconfirmed-transactions?format=json")
            response.raise_for_status()
            data = response.json()

            transactions = []
            btc_price = 95000  # Approximate, should fetch dynamically

            for tx in data.get("txs", [])[:50]:
                # Calculate total output value
                total_out = sum(out.get("value", 0) for out in tx.get("out", []))
                total_btc = total_out / 100_000_000  # Satoshi to BTC
                total_usd = total_btc * btc_price

                if total_usd >= self._min_value:
                    # Check if any output goes to known exchange
                    tx_type = TransactionType.UNKNOWN
                    to_owner = None
                    from_owner = None

                    for out in tx.get("out", []):
                        addr = out.get("addr", "")
                        if addr in KNOWN_EXCHANGES:
                            tx_type = TransactionType.EXCHANGE_INFLOW
                            to_owner = KNOWN_EXCHANGES[addr]
                            break

                    transactions.append(
                        WhaleTransaction(
                            timestamp=datetime.fromtimestamp(tx.get("time", 0)),
                            blockchain="bitcoin",
                            symbol="BTC",
                            amount=total_btc,
                            amount_usd=total_usd,
                            tx_type=tx_type,
                            from_owner=from_owner,
                            to_owner=to_owner,
                            tx_hash=tx.get("hash", ""),
                        )
                    )

            return transactions[:20]  # Limit results

        except Exception as e:
            logger.warning(f"Failed to fetch BTC transactions: {e}")
            return []

    def _classify_transaction(self, from_data: dict, to_data: dict) -> TransactionType:
        """Classify transaction type based on from/to owners."""
        from_owner = from_data.get("owner_type", "")
        to_owner = to_data.get("owner_type", "")

        if from_owner == "exchange" and to_owner == "exchange":
            return TransactionType.EXCHANGE_TO_EXCHANGE
        if to_owner == "exchange":
            return TransactionType.EXCHANGE_INFLOW
        if from_owner == "exchange":
            return TransactionType.EXCHANGE_OUTFLOW
        return TransactionType.UNKNOWN

    def _analyze_transactions(self, transactions: list[WhaleTransaction]) -> WhaleData:
        """Analyze list of transactions."""
        if not transactions:
            return self._create_empty_result()

        inflow_txs = [tx for tx in transactions if tx.tx_type == TransactionType.EXCHANGE_INFLOW]
        outflow_txs = [tx for tx in transactions if tx.tx_type == TransactionType.EXCHANGE_OUTFLOW]

        inflow_volume = sum(tx.amount_usd for tx in inflow_txs)
        outflow_volume = sum(tx.amount_usd for tx in outflow_txs)
        net_flow = inflow_volume - outflow_volume  # Positive = inflow (bearish)

        # Determine signal
        if outflow_volume > inflow_volume * 1.5:
            signal = WhaleSignal.ACCUMULATING
            signal_ru = "Накопление"
        elif inflow_volume > outflow_volume * 1.5:
            signal = WhaleSignal.DISTRIBUTING
            signal_ru = "Распределение"
        else:
            signal = WhaleSignal.NEUTRAL
            signal_ru = "Нейтрально"

        # Find largest transaction
        largest_tx = max(transactions, key=lambda x: x.amount_usd, default=None)

        # Sort by time (most recent first)
        sorted_txs = sorted(transactions, key=lambda x: x.timestamp, reverse=True)

        return WhaleData(
            timestamp=datetime.now(),
            transactions_24h=len(transactions),
            total_volume_usd_24h=sum(tx.amount_usd for tx in transactions),
            inflow_count=len(inflow_txs),
            outflow_count=len(outflow_txs),
            inflow_volume_usd=inflow_volume,
            outflow_volume_usd=outflow_volume,
            signal=signal,
            signal_ru=signal_ru,
            net_flow_usd=net_flow,
            recent_transactions=sorted_txs[:10],
            largest_tx=largest_tx,
        )

    def _create_empty_result(self) -> WhaleData:
        """Create empty result when no data available."""
        return WhaleData(
            timestamp=datetime.now(),
            transactions_24h=0,
            total_volume_usd_24h=0,
            inflow_count=0,
            outflow_count=0,
            inflow_volume_usd=0,
            outflow_volume_usd=0,
            signal=WhaleSignal.NEUTRAL,
            signal_ru="Нет данных",
            net_flow_usd=0,
            recent_transactions=[],
            largest_tx=None,
        )


# Global instance
_whale_tracker: WhaleTracker | None = None


def get_whale_tracker() -> WhaleTracker:
    """Get global whale tracker instance."""
    global _whale_tracker
    if _whale_tracker is None:
        _whale_tracker = WhaleTracker()
    return _whale_tracker
