"""Repository for sensor state persistence."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.sensor_state import SensorState

logger = logging.getLogger(__name__)


class SensorStateRepository:
    """Repository for async sensor state CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, unique_id: str, name: str, value: Any) -> SensorState | None:
        """Insert or update sensor state.

        Args:
            unique_id: Unique sensor identifier
            name: Sensor name
            value: Sensor value (will be JSON serialized if dict/list)

        Returns:
            SensorState if successful, None otherwise
        """
        try:
            # Serialize complex values to JSON
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False, default=str)
            else:
                value_str = str(value)

            stmt = insert(SensorState).values(
                unique_id=unique_id,
                name=name,
                value=value_str,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["unique_id"],
                set_={
                    "name": name,
                    "value": value_str,
                    "updated_at": datetime.now(UTC),
                },
            )
            await self.session.execute(stmt)
            await self.session.commit()

            return await self.get(unique_id)

        except Exception as e:
            logger.error(f"Failed to upsert sensor state {unique_id}: {e}")
            await self.session.rollback()
            return None

    async def get(self, unique_id: str) -> SensorState | None:
        """Get sensor state by unique_id."""
        try:
            result = await self.session.execute(select(SensorState).where(SensorState.unique_id == unique_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get sensor state {unique_id}: {e}")
            return None

    async def get_all(self) -> list[SensorState]:
        """Get all sensor states."""
        try:
            result = await self.session.execute(select(SensorState))
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get all sensor states: {e}")
            return []

    async def delete(self, unique_id: str) -> bool:
        """Delete sensor state."""
        try:
            state = await self.get(unique_id)
            if state:
                await self.session.delete(state)
                await self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete sensor state {unique_id}: {e}")
            await self.session.rollback()
            return False
