"""Base repository class for database operations.

Provides common CRUD operations with error handling.
"""

import logging
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# Type variable for model class
ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Base repository with common CRUD operations.

    Provides:
    - get_by_id: Get single record by primary key
    - get_all: Get all records with optional pagination
    - create: Create new record
    - update: Update existing record
    - delete: Delete record
    - count: Count records

    All operations include proper error handling and logging.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, id: Any) -> ModelT | None:
        """Get record by primary key.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        try:
            return await self.session.get(self.model, id)
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id {id}: {e}")
            raise DatabaseError(
                message=f"Failed to get {self.model.__name__}",
                operation="get_by_id",
            ) from e

    async def get_by_id_or_raise(self, id: Any) -> ModelT:
        """Get record by primary key or raise NotFoundError.

        Args:
            id: Primary key value

        Returns:
            Model instance

        Raises:
            NotFoundError: If record not found
        """
        result = await self.get_by_id(id)
        if result is None:
            raise NotFoundError(
                message=f"{self.model.__name__} not found",
                message_ru=f"{self.model.__name__} не найден",
                context=f"id={id}",
            )
        return result

    async def get_all(
        self,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ModelT]:
        """Get all records with optional pagination.

        Args:
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        try:
            query = select(self.model)

            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            result = await self.session.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to get {self.model.__name__} list",
                operation="get_all",
            ) from e

    async def create(self, instance: ModelT) -> ModelT:
        """Create new record.

        Args:
            instance: Model instance to create

        Returns:
            Created model instance
        """
        try:
            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)
            return instance

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to create {self.model.__name__}",
                operation="create",
            ) from e

    async def update(self, instance: ModelT) -> ModelT:
        """Update existing record.

        Args:
            instance: Model instance to update

        Returns:
            Updated model instance
        """
        try:
            await self.session.merge(instance)
            await self.session.commit()
            await self.session.refresh(instance)
            return instance

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to update {self.model.__name__}",
                operation="update",
            ) from e

    async def delete(self, instance: ModelT) -> None:
        """Delete record.

        Args:
            instance: Model instance to delete
        """
        try:
            await self.session.delete(instance)
            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to delete {self.model.__name__}",
                operation="delete",
            ) from e

    async def count(self) -> int:
        """Count total records.

        Returns:
            Number of records
        """
        try:
            from sqlalchemy import func

            query = select(func.count()).select_from(self.model)
            result = await self.session.execute(query)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to count {self.model.__name__}",
                operation="count",
            ) from e
