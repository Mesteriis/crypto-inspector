"""
On-Chain Metrics Module.

Fetches on-chain data from free APIs:
- Fear & Greed Index (Alternative.me)
- BTC Mempool stats (mempool.space)
- Hash Rate / Difficulty (blockchain.info)
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# API URLs
FEAR_GREED_URL = "https://api.alternative.me/fng/"
MEMPOOL_URL = "https://mempool.space/api"
BLOCKCHAIN_INFO_URL = "https://blockchain.info"


@dataclass
class FearGreedData:
    """Fear & Greed Index data."""

    value: int  # 0-100
    classification: str  # 'Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'
    timestamp: int
    time_until_update: int | None = None

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "classification": self.classification,
            "timestamp": self.timestamp,
            "time_until_update": self.time_until_update,
        }


@dataclass
class MempoolData:
    """Bitcoin mempool data."""

    tx_count: int
    total_fee: float  # BTC
    min_fee: float  # sat/vB
    median_fee: float  # sat/vB
    fastest_fee: float  # sat/vB

    def to_dict(self) -> dict:
        return {
            "tx_count": self.tx_count,
            "total_fee_btc": self.total_fee,
            "min_fee_sat_vb": self.min_fee,
            "median_fee_sat_vb": self.median_fee,
            "fastest_fee_sat_vb": self.fastest_fee,
        }


@dataclass
class NetworkData:
    """Bitcoin network data."""

    hash_rate: float  # EH/s
    difficulty: float
    block_height: int
    blocks_24h: int | None = None

    def to_dict(self) -> dict:
        return {
            "hash_rate_ehs": self.hash_rate,
            "difficulty": self.difficulty,
            "block_height": self.block_height,
            "blocks_24h": self.blocks_24h,
        }


@dataclass
class OnChainMetrics:
    """Combined on-chain metrics."""

    fear_greed: FearGreedData | None = None
    mempool: MempoolData | None = None
    network: NetworkData | None = None
    timestamp: int = 0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "fear_greed": self.fear_greed.to_dict() if self.fear_greed else None,
            "mempool": self.mempool.to_dict() if self.mempool else None,
            "network": self.network.to_dict() if self.network else None,
        }


class OnChainAnalyzer:
    """Fetches and analyzes on-chain metrics."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": "CryptoInspect/1.0"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_fear_greed(self) -> FearGreedData | None:
        """
        Fetch Fear & Greed Index from Alternative.me.

        Returns:
            FearGreedData or None on error
        """
        client = await self._get_client()

        try:
            response = await client.get(FEAR_GREED_URL)
            response.raise_for_status()
            data = response.json()

            if "data" not in data or not data["data"]:
                logger.error("Invalid Fear & Greed response")
                return None

            fg = data["data"][0]

            return FearGreedData(
                value=int(fg["value"]),
                classification=fg["value_classification"],
                timestamp=int(fg["timestamp"]),
                time_until_update=int(fg.get("time_until_update", 0)),
            )

        except httpx.HTTPError as e:
            logger.error(f"Fear & Greed API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Fear & Greed parsing error: {e}")
            return None

    async def fetch_mempool(self) -> MempoolData | None:
        """
        Fetch mempool stats from mempool.space.

        Returns:
            MempoolData or None on error
        """
        client = await self._get_client()

        try:
            # Fetch mempool stats
            response = await client.get(f"{MEMPOOL_URL}/mempool")
            response.raise_for_status()
            mempool = response.json()

            # Fetch recommended fees
            fee_response = await client.get(f"{MEMPOOL_URL}/v1/fees/recommended")
            fee_response.raise_for_status()
            fees = fee_response.json()

            return MempoolData(
                tx_count=mempool.get("count", 0),
                total_fee=mempool.get("total_fee", 0) / 100_000_000,  # sats to BTC
                min_fee=fees.get("minimumFee", 1),
                median_fee=fees.get("halfHourFee", 5),
                fastest_fee=fees.get("fastestFee", 10),
            )

        except httpx.HTTPError as e:
            logger.error(f"Mempool API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Mempool parsing error: {e}")
            return None

    async def fetch_network_stats(self) -> NetworkData | None:
        """
        Fetch BTC network stats.

        Returns:
            NetworkData or None on error
        """
        client = await self._get_client()

        try:
            # Fetch difficulty
            diff_response = await client.get(f"{MEMPOOL_URL}/v1/mining/difficulty-adjustments")
            diff_data = diff_response.json() if diff_response.status_code == 200 else []

            # Fetch hashrate
            hash_response = await client.get(f"{MEMPOOL_URL}/v1/mining/hashrate/1m")
            hash_data = hash_response.json() if hash_response.status_code == 200 else {}

            # Get latest block
            tip_response = await client.get(f"{MEMPOOL_URL}/blocks/tip/height")
            block_height = int(tip_response.text) if tip_response.status_code == 200 else 0

            # Calculate hash rate (from difficulty if not available)
            hash_rate = 0.0
            if hash_data and "hashrates" in hash_data and hash_data["hashrates"]:
                # Hash rate in H/s, convert to EH/s
                hash_rate = hash_data["hashrates"][-1].get("avgHashrate", 0) / 1e18
            elif diff_data:
                # Estimate from difficulty (rough approximation)
                difficulty = diff_data[0].get("difficultyChange", 0) + diff_data[0].get(
                    "previousDifficulty", 0
                )
                hash_rate = difficulty * 2**32 / 600 / 1e18  # EH/s

            difficulty = diff_data[0].get("difficulty", 0) if diff_data else 0

            return NetworkData(
                hash_rate=round(hash_rate, 2),
                difficulty=difficulty,
                block_height=block_height,
            )

        except httpx.HTTPError as e:
            logger.error(f"Network stats API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Network stats parsing error: {e}")
            return None

    async def analyze(self) -> OnChainMetrics:
        """
        Fetch all on-chain metrics.

        Returns:
            OnChainMetrics with all available data
        """
        result = OnChainMetrics(timestamp=int(datetime.now().timestamp() * 1000))

        # Fetch all metrics concurrently
        import asyncio

        fg_task = asyncio.create_task(self.fetch_fear_greed())
        mempool_task = asyncio.create_task(self.fetch_mempool())
        network_task = asyncio.create_task(self.fetch_network_stats())

        result.fear_greed = await fg_task
        result.mempool = await mempool_task
        result.network = await network_task

        return result

    def get_fear_greed_signal(self, fg_value: int) -> dict:
        """
        Get trading signal from Fear & Greed value.

        Args:
            fg_value: Fear & Greed Index (0-100)

        Returns:
            Signal dictionary
        """
        if fg_value < 20:
            return {
                "signal": "strong_buy",
                "description": "Extreme Fear - Excellent buying opportunity",
                "score_adjustment": 25,
            }
        elif fg_value < 35:
            return {
                "signal": "buy",
                "description": "Fear - Good buying opportunity",
                "score_adjustment": 15,
            }
        elif fg_value > 80:
            return {
                "signal": "strong_sell",
                "description": "Extreme Greed - Consider taking profits",
                "score_adjustment": -25,
            }
        elif fg_value > 65:
            return {
                "signal": "sell",
                "description": "Greed - Caution advised",
                "score_adjustment": -15,
            }
        else:
            return {
                "signal": "neutral",
                "description": "Neutral - No strong signal",
                "score_adjustment": 0,
            }
