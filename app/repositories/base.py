"""Base repository with common CRUD operations."""

import logging
from typing import Any, TypeVar, Generic

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.base import Base

T = TypeVar("T", bound=Base)
logger = logging.getLogger(__name__)


class BaseRepository(Generic[T]):
    """Base repository providing common database operations.

    Subclasses must set `model` to the SQLAlchemy model class.
    """

    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, record_id: int) -> T | None:
        """Get a record by its primary key."""
        return await self.session.get(self.model, record_id)

    async def get_all(self, **filters: Any) -> list[T]:
        """Get all records matching the given filters."""
        query = select(self.model)
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> T:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()  # Get the ID without committing
        return instance

    async def update(self, record: T, **kwargs: Any) -> T:
        """Update an existing record."""
        for key, value in kwargs.items():
            setattr(record, key, value)
        await self.session.flush()
        return record

    async def delete_record(self, record: T) -> None:
        """Delete a record."""
        await self.session.delete(record)
        await self.session.flush()
