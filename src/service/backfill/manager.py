"""
Backfill Manager.

Orchestrates historical data backfill for:
- Crypto candlesticks (10 years)
- Traditional assets (1 year)

Runs on startup to ensure data completeness.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from service.backfill.crypto_backfill import get_crypto_backfill
from service.backfill.traditional_backfill import get_traditional_backfill

logger = logging.getLogger(__name__)


class BackfillStatus(Enum):
    """Backfill status."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class BackfillProgress:
    """Backfill progress info."""

    status: BackfillStatus = BackfillStatus.IDLE
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Crypto progress
    crypto_symbols_total: int = 0
    crypto_symbols_done: int = 0
    crypto_symbols_failed: int = 0
    crypto_candles_total: int = 0

    # Traditional progress
    traditional_assets_total: int = 0
    traditional_assets_done: int = 0
    traditional_assets_failed: int = 0
    traditional_records_total: int = 0

    # Current task
    current_task: str = ""
    error_message: str | None = None
    failed_symbols: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "crypto": {
                "symbols_total": self.crypto_symbols_total,
                "symbols_done": self.crypto_symbols_done,
                "symbols_failed": self.crypto_symbols_failed,
                "candles_total": self.crypto_candles_total,
            },
            "traditional": {
                "assets_total": self.traditional_assets_total,
                "assets_done": self.traditional_assets_done,
                "assets_failed": self.traditional_assets_failed,
                "records_total": self.traditional_records_total,
            },
            "current_task": self.current_task,
            "error": self.error_message,
            "failed_symbols": self.failed_symbols,
        }


# Marker file to track first run
BACKFILL_MARKER_FILE = "/data/backfill_completed"


class BackfillManager:
    """
    Backfill manager.

    Orchestrates historical data backfill on startup.
    """

    def __init__(
        self,
        crypto_years: int = 10,
        traditional_years: int = 1,
        crypto_intervals: list[str] | None = None,
    ):
        self.crypto_years = crypto_years
        self.traditional_years = traditional_years
        self.crypto_intervals = crypto_intervals or ["1d", "4h", "1h"]

        self._progress = BackfillProgress()
        self._is_running = False

    def _get_symbols(self) -> list[str]:
        """Get configured crypto symbols (deprecated - use get_currency_list instead)."""
        symbols_env = os.environ.get("HA_SYMBOLS", "BTC/USDT,ETH/USDT")
        return [s.strip() for s in symbols_env.split(",") if s.strip()]

    def _get_currency_list(self) -> list[str]:
        """Get the dynamic currency list from Home Assistant input_select helper.

        This is the single source of truth for currency selections across the application.

        Returns:
            List of currency symbols (e.g., ["BTC/USDT", "ETH/USDT"])
        """
        from service.ha import get_currency_list as get_dynamic_currency_list

        return get_dynamic_currency_list()

    def _is_first_run(self) -> bool:
        """Check if this is the first run (no backfill marker)."""
        marker = Path(BACKFILL_MARKER_FILE)
        return not marker.exists()

    def _mark_completed(self):
        """Mark backfill as completed."""
        try:
            marker = Path(BACKFILL_MARKER_FILE)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(datetime.now(UTC).isoformat())
        except Exception as e:
            logger.warning(f"Could not write backfill marker: {e}")

    async def check_and_backfill(self, force: bool = False) -> bool:
        """
        Check for missing data and backfill if needed.

        Args:
            force: Force backfill even if marker exists

        Returns:
            True if backfill was performed
        """
        if self._is_running:
            logger.warning("Backfill already running")
            return False

        # Check if first run or forced
        if not force and not self._is_first_run():
            logger.info("Backfill already completed (marker exists)")
            return False

        logger.info("Starting initial data backfill...")
        self._is_running = True
        self._progress.status = BackfillStatus.RUNNING
        self._progress.started_at = datetime.now(UTC)

        try:
            # Backfill crypto
            await self._backfill_crypto()

            # Backfill traditional
            await self._backfill_traditional()

            # Mark as completed
            self._mark_completed()

            self._progress.status = BackfillStatus.COMPLETED
            self._progress.completed_at = datetime.now(UTC)

            logger.info(
                f"Backfill completed: "
                f"{self._progress.crypto_candles_total} crypto candles, "
                f"{self._progress.traditional_records_total} traditional records"
            )

            return True

        except Exception as e:
            logger.error(f"Backfill failed: {e}")
            self._progress.status = BackfillStatus.ERROR
            self._progress.error_message = str(e)
            return False

        finally:
            self._is_running = False

    async def _backfill_crypto(self):
        """
        Backfill crypto candlesticks.
        
        Raises:
            RuntimeError: If any symbol fails to backfill (strict mode)
        """
        symbols = self._get_currency_list()
        intervals = self.crypto_intervals

        self._progress.crypto_symbols_total = len(symbols) * len(intervals)
        self._progress.crypto_symbols_done = 0
        self._progress.crypto_symbols_failed = 0
        self._progress.failed_symbols = []

        crypto_backfill = get_crypto_backfill()

        for symbol in symbols:
            for interval in intervals:
                key = f"{symbol}_{interval}"
                self._progress.current_task = f"Crypto: {symbol} {interval}"
                logger.info(f"Backfilling {symbol} {interval}...")

                try:
                    count = await crypto_backfill.backfill_symbol(
                        symbol=symbol,
                        interval=interval,
                        years=self.crypto_years,
                    )

                    if count == 0:
                        # No data received - consider as failure
                        logger.error(f"No data received for {key}")
                        self._progress.crypto_symbols_failed += 1
                        self._progress.failed_symbols.append(key)
                    else:
                        self._progress.crypto_candles_total += count
                        self._progress.crypto_symbols_done += 1

                except Exception as e:
                    logger.error(f"Error backfilling {key}: {e}")
                    self._progress.crypto_symbols_failed += 1
                    self._progress.failed_symbols.append(key)

                # Small delay between requests
                await asyncio.sleep(0.5)

        # Check if all symbols were successfully backfilled
        if self._progress.crypto_symbols_failed > 0:
            raise RuntimeError(
                f"Crypto backfill FAILED: {self._progress.crypto_symbols_failed}/{self._progress.crypto_symbols_total} "
                f"symbols failed. Failed: {self._progress.failed_symbols}"
            )

    async def _backfill_traditional(self):
        """
        Backfill traditional assets.
        
        Raises:
            RuntimeError: If any asset fails to backfill (strict mode)
        """
        from service.backfill.traditional_backfill import TRADITIONAL_ASSETS

        self._progress.traditional_assets_total = len(TRADITIONAL_ASSETS)
        self._progress.traditional_assets_done = 0
        self._progress.traditional_assets_failed = 0

        traditional_backfill = get_traditional_backfill()

        for symbol in TRADITIONAL_ASSETS:
            self._progress.current_task = f"Traditional: {symbol}"
            logger.info(f"Backfilling traditional asset: {symbol}...")

            try:
                count = await traditional_backfill.backfill_asset(
                    symbol=symbol,
                    years=self.traditional_years,
                )

                if count == 0:
                    logger.error(f"No data received for traditional asset: {symbol}")
                    self._progress.traditional_assets_failed += 1
                    self._progress.failed_symbols.append(f"traditional:{symbol}")
                else:
                    self._progress.traditional_records_total += count
                    self._progress.traditional_assets_done += 1

            except Exception as e:
                logger.error(f"Error backfilling {symbol}: {e}")
                self._progress.traditional_assets_failed += 1
                self._progress.failed_symbols.append(f"traditional:{symbol}")

            # Longer delay to avoid Yahoo Finance rate limiting
            await asyncio.sleep(3.0)

        # Check if all assets were successfully backfilled
        if self._progress.traditional_assets_failed > 0:
            raise RuntimeError(
                f"Traditional backfill FAILED: {self._progress.traditional_assets_failed}/{self._progress.traditional_assets_total} "
                f"assets failed"
            )

    async def backfill_crypto(
        self,
        symbols: list[str] | None = None,
        intervals: list[str] | None = None,
        years: int | None = None,
    ) -> dict[str, int]:
        """
        Backfill crypto candlesticks manually.

        Args:
            symbols: Symbols to backfill (default: configured)
            intervals: Intervals to backfill (default: 1d, 4h, 1h)
            years: Years of history (default: 10)

        Returns:
            Dict of {symbol_interval: candle_count}
        """
        symbols = symbols or self._get_symbols()
        intervals = intervals or self.crypto_intervals
        years = years or self.crypto_years

        crypto_backfill = get_crypto_backfill()
        results = {}

        for symbol in symbols:
            for interval in intervals:
                key = f"{symbol}_{interval}"
                try:
                    count = await crypto_backfill.backfill_symbol(
                        symbol=symbol,
                        interval=interval,
                        years=years,
                    )
                    results[key] = count
                except Exception as e:
                    logger.error(f"Error backfilling {key}: {e}")
                    results[key] = 0

                await asyncio.sleep(0.5)

        return results

    async def backfill_traditional(
        self,
        symbols: list[str] | None = None,
        years: int | None = None,
    ) -> dict[str, int]:
        """
        Backfill traditional assets manually.

        Args:
            symbols: Symbols to backfill (default: all)
            years: Years of history (default: 1)

        Returns:
            Dict of {symbol: record_count}
        """
        from service.backfill.traditional_backfill import TRADITIONAL_ASSETS

        symbols = symbols or list(TRADITIONAL_ASSETS.keys())
        years = years or self.traditional_years

        traditional_backfill = get_traditional_backfill()
        results = {}

        for symbol in symbols:
            try:
                count = await traditional_backfill.backfill_asset(
                    symbol=symbol,
                    years=years,
                )
                results[symbol] = count
            except Exception as e:
                logger.error(f"Error backfilling {symbol}: {e}")
                results[symbol] = 0

            await asyncio.sleep(0.3)

        return results

    async def detect_all_gaps(self) -> dict[str, list[tuple[int, int]]]:
        """
        Detect gaps in all crypto data.

        Returns:
            Dict of {symbol_interval: [(gap_start, gap_end), ...]}
        """
        symbols = self._get_currency_list()
        intervals = self.crypto_intervals

        crypto_backfill = get_crypto_backfill()
        gaps = {}

        for symbol in symbols:
            for interval in intervals:
                key = f"{symbol}_{interval}"
                symbol_gaps = await crypto_backfill.detect_gaps(symbol, interval)
                if symbol_gaps:
                    gaps[key] = symbol_gaps

        return gaps

    async def fill_all_gaps(self) -> dict[str, int]:
        """
        Fill all detected gaps.

        Returns:
            Dict of {symbol_interval: filled_count}
        """
        all_gaps = await self.detect_all_gaps()

        if not all_gaps:
            logger.info("No gaps detected")
            return {}

        crypto_backfill = get_crypto_backfill()
        results = {}

        for key, gaps in all_gaps.items():
            symbol, interval = key.rsplit("_", 1)
            filled = await crypto_backfill.fill_gaps(symbol, interval, gaps)
            results[key] = filled
            await asyncio.sleep(0.5)

        return results

    @property
    def progress(self) -> BackfillProgress:
        """Get current progress."""
        return self._progress

    @property
    def is_running(self) -> bool:
        """Check if backfill is running."""
        return self._is_running


# Global instance
_backfill_manager: BackfillManager | None = None


def get_backfill_manager() -> BackfillManager:
    """Get or create backfill manager instance."""
    global _backfill_manager
    if _backfill_manager is None:
        # Get config from environment
        crypto_years = int(os.environ.get("BACKFILL_CRYPTO_YEARS", "10"))
        traditional_years = int(os.environ.get("BACKFILL_TRADITIONAL_YEARS", "1"))
        intervals_str = os.environ.get("BACKFILL_INTERVALS", "1d,4h,1h")
        intervals = [i.strip() for i in intervals_str.split(",")]

        _backfill_manager = BackfillManager(
            crypto_years=crypto_years,
            traditional_years=traditional_years,
            crypto_intervals=intervals,
        )
    return _backfill_manager
