"""
ETH Gas Tracker.

Tracks Ethereum gas prices for transaction timing:
- Slow/Standard/Fast gas prices in Gwei
- Gas status classification (Cheap/Normal/Expensive)

Data sources:
- Etherscan API (requires API key)
- Blocknative API
- ETH Gas Station (deprecated)
- Or fallback to on-chain estimation
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

# API endpoints
ETHERSCAN_API_URL = "https://api.etherscan.io/api"
BLOCKNATIVE_API_URL = "https://api.blocknative.com/gasprices/blockprices"


class GasStatus(Enum):
    """Gas price status classification."""

    VERY_CHEAP = "very_cheap"  # < 10 Gwei
    CHEAP = "cheap"  # 10-25 Gwei
    NORMAL = "normal"  # 25-50 Gwei
    EXPENSIVE = "expensive"  # 50-100 Gwei
    VERY_EXPENSIVE = "very_expensive"  # > 100 Gwei


@dataclass
class GasData:
    """ETH gas price data."""

    timestamp: datetime
    slow: float  # Gwei - safe low, ~10 min
    standard: float  # Gwei - average, ~3 min
    fast: float  # Gwei - fast, ~30 sec
    instant: float | None  # Gwei - instant, for flashbots/MEV
    base_fee: float | None  # Current base fee
    priority_fee_slow: float | None  # Priority fee for slow
    priority_fee_fast: float | None  # Priority fee for fast
    status: GasStatus
    status_ru: str
    source: str  # Data source used

    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "slow": round(self.slow, 1),
            "standard": round(self.standard, 1),
            "fast": round(self.fast, 1),
            "instant": round(self.instant, 1) if self.instant else None,
            "base_fee": round(self.base_fee, 1) if self.base_fee else None,
            "priority_slow": (round(self.priority_fee_slow, 1) if self.priority_fee_slow else None),
            "priority_fast": (round(self.priority_fee_fast, 1) if self.priority_fee_fast else None),
            "status": self.status.value,
            "status_ru": self.status_ru,
            "status_emoji": self._get_status_emoji(),
            "source": self.source,
            "cost_estimate_usd": self._estimate_costs(),
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _get_status_emoji(self) -> str:
        """Get emoji for status."""
        emoji_map = {
            GasStatus.VERY_CHEAP: "🟢🟢",
            GasStatus.CHEAP: "🟢",
            GasStatus.NORMAL: "🟡",
            GasStatus.EXPENSIVE: "🟠",
            GasStatus.VERY_EXPENSIVE: "🔴",
        }
        return emoji_map.get(self.status, "⚪")

    def _estimate_costs(self) -> dict:
        """Estimate transaction costs in USD (assuming ETH ~$3500)."""
        eth_price = 3500  # Rough estimate, should be fetched dynamically
        gas_units = {
            "transfer": 21000,
            "erc20_transfer": 65000,
            "swap": 150000,
            "nft_mint": 100000,
        }

        costs = {}
        for tx_type, gas_limit in gas_units.items():
            # Cost = gas_limit * gas_price_in_gwei * 1e-9 * eth_price
            cost_slow = gas_limit * self.slow * 1e-9 * eth_price
            cost_fast = gas_limit * self.fast * 1e-9 * eth_price
            costs[tx_type] = {
                "slow": f"${cost_slow:.2f}",
                "fast": f"${cost_fast:.2f}",
            }

        return costs

    def _get_summary(self) -> str:
        """Get English summary."""
        status_map = {
            GasStatus.VERY_CHEAP: "Very cheap gas",
            GasStatus.CHEAP: "Cheap gas",
            GasStatus.NORMAL: "Normal gas",
            GasStatus.EXPENSIVE: "Expensive gas",
            GasStatus.VERY_EXPENSIVE: "Very expensive gas",
        }
        status_text = status_map.get(self.status, "Unknown")
        return f"{status_text}: {self.standard:.0f} Gwei (standard)"

    def _get_summary_ru(self) -> str:
        """Get Russian summary."""
        return f"{self.status_ru}: {self.standard:.0f} Gwei (стандарт)"


class GasTracker:
    """
    ETH Gas price tracker.

    Supports multiple data sources with fallback.
    """

    def __init__(self, etherscan_api_key: str | None = None, timeout: float = 15.0):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout
        # Support both ENV formats: ETHERSCAN_API_KEY and etherscan_api_key
        self._etherscan_key = etherscan_api_key or os.environ.get("ETHERSCAN_API_KEY") or os.environ.get("etherscan_api_key")

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

    async def get_gas_prices(self) -> GasData:
        """
        Get current ETH gas prices.

        Tries multiple sources in order:
        1. Etherscan (if API key available)
        2. Blocknative
        3. Public endpoints

        Returns:
            GasData with current prices (always returns a value, defaults if all fail)
        """
        client = await self._get_client()

        # Try Etherscan first if API key available
        if self._etherscan_key:
            try:
                result = await self._fetch_etherscan(client)
                logger.info(f"Gas prices from Etherscan: {result.standard} Gwei")
                return result
            except Exception as e:
                logger.warning(f"Etherscan fetch failed: {e}")

        # Try public endpoints
        try:
            result = await self._fetch_public_api(client)
            logger.info(f"Gas prices from {result.source}: {result.standard} Gwei")
            return result
        except Exception as e:
            logger.warning(f"Public API fetch failed: {e}")

        # Return default values - always return something
        logger.info("Using default gas values")
        return self._create_default_result()

    async def _fetch_etherscan(self, client: httpx.AsyncClient) -> GasData:
        """Fetch gas prices from Etherscan."""
        params = {
            "module": "gastracker",
            "action": "gasoracle",
            "apikey": self._etherscan_key,
        }

        response = await client.get(ETHERSCAN_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "1":
            raise ValueError(f"Etherscan error: {data.get('message')}")

        result = data.get("result", {})

        slow = float(result.get("SafeGasPrice", 20))
        standard = float(result.get("ProposeGasPrice", 25))
        fast = float(result.get("FastGasPrice", 35))
        base_fee = float(result.get("suggestBaseFee", 0)) or None

        return GasData(
            timestamp=datetime.now(),
            slow=slow,
            standard=standard,
            fast=fast,
            instant=fast * 1.2,  # Estimate instant as 120% of fast
            base_fee=base_fee,
            priority_fee_slow=slow - base_fee if base_fee else None,
            priority_fee_fast=fast - base_fee if base_fee else None,
            status=self._classify_status(standard),
            status_ru=self._get_status_ru(standard),
            source="etherscan",
        )

    async def _fetch_public_api(self, client: httpx.AsyncClient) -> GasData:
        """Fetch from public API (no key required)."""
        # Try Beaconcha.in first (most reliable free API)
        try:
            response = await client.get("https://beaconcha.in/api/v1/execution/gasnow")
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Beaconcha.in response: {data}")
            
            # Beaconcha.in returns data directly, not nested under "data"
            gas_data = data.get("data", data)  # Try both formats
            rapid = gas_data.get("rapid", 35e9)
            fast = gas_data.get("fast", 30e9)
            standard = gas_data.get("standard", 25e9)
            slow = gas_data.get("slow", 20e9)
            
            # Convert Wei to Gwei if values are large (> 1000)
            if slow > 1000:
                slow = slow / 1e9
            if standard > 1000:
                standard = standard / 1e9
            if fast > 1000:
                fast = fast / 1e9
            if rapid > 1000:
                rapid = rapid / 1e9
            
            return GasData(
                timestamp=datetime.now(),
                slow=slow,
                standard=standard,
                fast=fast,
                instant=rapid,
                base_fee=None,
                priority_fee_slow=None,
                priority_fee_fast=None,
                status=self._classify_status(standard),
                status_ru=self._get_status_ru(standard),
                source="beaconcha.in",
            )
        except Exception as e:
            logger.warning(f"Beaconcha.in fetch failed: {e}")

        # Try ETH Gas API
        try:
            response = await client.get("https://api.ethgasstation.info/api/ethgasAPI.json")
            response.raise_for_status()
            data = response.json()

            # ETH Gas Station returns values in 10x Gwei
            slow = float(data.get("safeLow", 200)) / 10
            standard = float(data.get("average", 250)) / 10
            fast = float(data.get("fast", 350)) / 10
            fastest = float(data.get("fastest", 400)) / 10

            return GasData(
                timestamp=datetime.now(),
                slow=slow,
                standard=standard,
                fast=fast,
                instant=fastest,
                base_fee=None,
                priority_fee_slow=None,
                priority_fee_fast=None,
                status=self._classify_status(standard),
                status_ru=self._get_status_ru(standard),
                source="ethgasstation",
            )
        except Exception:
            pass

        # Try Blocknative (free tier)
        try:
            response = await client.get("https://api.blocknative.com/gasprices/blockprices")
            response.raise_for_status()
            data = response.json()

            block_prices = data.get("blockPrices", [{}])[0]
            estimated = block_prices.get("estimatedPrices", [])

            if estimated:
                slow = next(
                    (e.get("price", 20) for e in estimated if e.get("confidence") == 80),
                    20,
                )
                standard = next(
                    (e.get("price", 25) for e in estimated if e.get("confidence") == 90),
                    25,
                )
                fast = next(
                    (e.get("price", 35) for e in estimated if e.get("confidence") == 99),
                    35,
                )

                base_fee = block_prices.get("baseFeePerGas")

                return GasData(
                    timestamp=datetime.now(),
                    slow=slow,
                    standard=standard,
                    fast=fast,
                    instant=fast * 1.2,
                    base_fee=base_fee,
                    priority_fee_slow=None,
                    priority_fee_fast=None,
                    status=self._classify_status(standard),
                    status_ru=self._get_status_ru(standard),
                    source="blocknative",
                )
        except Exception:
            pass

        raise ValueError("All gas API sources failed")

    def _classify_status(self, standard_gwei: float) -> GasStatus:
        """Classify gas status based on standard price."""
        if standard_gwei < 10:
            return GasStatus.VERY_CHEAP
        if standard_gwei < 25:
            return GasStatus.CHEAP
        if standard_gwei < 50:
            return GasStatus.NORMAL
        if standard_gwei < 100:
            return GasStatus.EXPENSIVE
        return GasStatus.VERY_EXPENSIVE

    def _get_status_ru(self, standard_gwei: float) -> str:
        """Get Russian status text."""
        status = self._classify_status(standard_gwei)
        status_map = {
            GasStatus.VERY_CHEAP: "Очень дёшево",
            GasStatus.CHEAP: "Дёшево",
            GasStatus.NORMAL: "Норма",
            GasStatus.EXPENSIVE: "Дорого",
            GasStatus.VERY_EXPENSIVE: "Очень дорого",
        }
        return status_map.get(status, "Неизвестно")

    def _create_default_result(self) -> GasData:
        """Create default result when all sources fail."""
        return GasData(
            timestamp=datetime.now(),
            slow=20,
            standard=25,
            fast=35,
            instant=45,
            base_fee=None,
            priority_fee_slow=None,
            priority_fee_fast=None,
            status=GasStatus.NORMAL,
            status_ru="Нет данных",
            source="default",
        )


# Global instance
_gas_tracker: GasTracker | None = None


def get_gas_tracker() -> GasTracker:
    """Get global gas tracker instance."""
    global _gas_tracker
    if _gas_tracker is None:
        _gas_tracker = GasTracker()
    return _gas_tracker
