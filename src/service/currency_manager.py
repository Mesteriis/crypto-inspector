"""
Dynamic Currency List Management Service.

Handles automatic cleanup of removed currencies and loading of new currencies.
"""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import text

from models.session import async_session_maker
from service.ha import get_currency_list

logger = logging.getLogger(__name__)


class CurrencyListManager:
    """
    Manages dynamic currency list changes including cleanup and loading.

    Monitors the input_select helper for currency list changes and:
    1. Cleans up database data for removed currencies
    2. Initiates historical data loading for new currencies
    3. Updates notification systems
    """

    def __init__(self):
        self._previous_currencies: set[str] = set()
        self._cleanup_enabled = True
        self._loading_enabled = True

    async def initialize(self) -> None:
        """Initialize with current currency list."""
        current_currencies = set(self._get_current_currencies())
        self._previous_currencies = current_currencies
        logger.info(f"Currency list manager initialized with {len(current_currencies)} currencies")

    async def check_for_changes(self) -> None:
        """Check for currency list changes and handle them."""
        current_currencies = set(self._get_current_currencies())
        previous_currencies = self._previous_currencies

        if current_currencies == previous_currencies:
            return  # No changes

        # Identify added and removed currencies
        added = current_currencies - previous_currencies
        removed = previous_currencies - current_currencies

        logger.info(f"Currency list changed - Added: {added}, Removed: {removed}")

        # Handle removals (cleanup)
        if removed and self._cleanup_enabled:
            await self._handle_removed_currencies(removed)

        # Handle additions (loading)
        if added and self._loading_enabled:
            await self._handle_added_currencies(added)

        # Update notification systems
        await self._update_notification_systems(added, removed)

        # Update previous state
        self._previous_currencies = current_currencies

    def _get_current_currencies(self) -> list[str]:
        """Get current currency list from dynamic source."""
        return get_currency_list()

    async def _handle_removed_currencies(self, removed_currencies: set[str]) -> None:
        """Clean up database data for removed currencies."""
        logger.info(f"Cleaning up data for removed currencies: {removed_currencies}")

        try:
            async with async_session_maker() as session:
                for currency in removed_currencies:
                    # Clean up candlestick records
                    await self._cleanup_candlestick_data(session, currency)

                    # Clean up ML prediction records
                    await self._cleanup_ml_prediction_data(session, currency)

                    # Clean up any other currency-specific data
                    await self._cleanup_other_currency_data(session, currency)

                await session.commit()

            logger.info(f"Successfully cleaned up data for {len(removed_currencies)} currencies")

        except Exception as e:
            logger.error(f"Error cleaning up removed currencies {removed_currencies}: {e}")

    async def _cleanup_candlestick_data(self, session, currency: str) -> int:
        """Clean up candlestick records for a currency."""
        try:
            # Delete all candlestick records for this currency (all intervals)
            stmt = text("""
                DELETE FROM candlestick_records
                WHERE symbol = :symbol
            """)
            result = await session.execute(stmt, {"symbol": currency})
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} candlestick records for {currency}")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up candlestick data for {currency}: {e}")
            return 0

    async def _cleanup_ml_prediction_data(self, session, currency: str) -> int:
        """Clean up ML prediction records for a currency."""
        try:
            from sqlalchemy import text

            stmt = text("""
                DELETE FROM ml_prediction_records
                WHERE symbol = :symbol
            """)
            result = await session.execute(stmt, {"symbol": currency})
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} ML prediction records for {currency}")
            return deleted_count
        except Exception as e:
            # Table might not exist, that's OK
            logger.debug(f"ML prediction table cleanup skipped for {currency}: {e}")
            return 0

    async def _cleanup_other_currency_data(self, session, currency: str) -> None:
        """Clean up other currency-specific data (future extensibility)."""
        # Placeholder for other tables that might store currency data
        # This could include portfolio data, watchlists, etc.
        pass

    async def _handle_added_currencies(self, added_currencies: set[str]) -> None:
        """Initiate historical data loading for newly added currencies."""
        logger.info(f"Loading historical data for new currencies: {added_currencies}")

        try:
            from service.backfill.manager import get_backfill_manager

            backfill_manager = get_backfill_manager()

            # Load historical data for each new currency
            for currency in added_currencies:
                await self._load_historical_data(backfill_manager, currency)

        except Exception as e:
            logger.error(f"Error loading historical data for added currencies {added_currencies}: {e}")

    async def _load_historical_data(self, backfill_manager, currency: str) -> None:
        """Load historical data for a single currency."""
        try:
            logger.info(f"Starting historical data load for {currency}")

            # Load different intervals with different timeframes
            intervals_config = [
                ("1d", 2),  # 2 years daily data
                ("4h", 1),  # 1 year 4-hour data
                ("1h", 6),  # 6 months hourly data
            ]

            total_loaded = 0
            for interval, years in intervals_config:
                try:
                    count = await backfill_manager.backfill_crypto(
                        symbols=[currency], intervals=[interval], years=years
                    )
                    loaded_count = count.get(f"{currency}_{interval}", 0)
                    total_loaded += loaded_count
                    logger.info(f"Loaded {loaded_count} {interval} candles for {currency}")

                    # Brief delay between intervals
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error loading {interval} data for {currency}: {e}")

            logger.info(f"Completed historical data load for {currency}: {total_loaded} total candles")

        except Exception as e:
            logger.error(f"Error in historical data loading for {currency}: {e}")

    async def _update_notification_systems(self, added: set[str], removed: set[str]) -> None:
        """Update notification systems for currency list changes."""
        try:
            # Update Home Assistant notifications about currency changes
            from service.ha_integration import notify

            if added:
                message = f"📈 New currencies added: {', '.join(sorted(added))}\nHistorical data loading initiated."
                await notify(message=message, title="Currency List Updated", notification_id="currency_added")

            if removed:
                message = f"📉 Currencies removed: {', '.join(sorted(removed))}\nAssociated data has been cleaned up."
                await notify(message=message, title="Currency List Updated", notification_id="currency_removed")

            logger.info("Notification systems updated for currency list changes")

        except Exception as e:
            logger.error(f"Error updating notification systems: {e}")

    def enable_cleanup(self, enabled: bool = True) -> None:
        """Enable or disable automatic cleanup of removed currencies."""
        self._cleanup_enabled = enabled
        logger.info(f"Currency cleanup {'enabled' if enabled else 'disabled'}")

    def enable_loading(self, enabled: bool = True) -> None:
        """Enable or disable automatic loading of new currencies."""
        self._loading_enabled = enabled
        logger.info(f"Currency loading {'enabled' if enabled else 'disabled'}")

    async def manual_cleanup(self, currencies: list[str]) -> dict:
        """Manually trigger cleanup for specific currencies."""
        removed_set = set(currencies)
        await self._handle_removed_currencies(removed_set)
        return {
            "status": "completed",
            "currencies_cleaned": list(removed_set),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def manual_load(self, currencies: list[str]) -> dict:
        """Manually trigger historical data loading for specific currencies."""
        added_set = set(currencies)
        await self._handle_added_currencies(added_set)
        return {"status": "completed", "currencies_loaded": list(added_set), "timestamp": datetime.now(UTC).isoformat()}


# Global instance
_currency_manager = None


def get_currency_manager() -> CurrencyListManager:
    """Get singleton currency list manager instance."""
    global _currency_manager
    if _currency_manager is None:
        _currency_manager = CurrencyListManager()
    return _currency_manager
