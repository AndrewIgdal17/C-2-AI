"""
Database configuration and session management
for the AI Virtual Agent Quickstart application.

This module sets up SQLAlchemy with async PostgreSQL support,
configures the database connection, and provides utilities
for managing database sessions and transactions.
"""

from typing import Generator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> Generator[AsyncSession, None, None]:
    """
    Dependency function that provides database sessions for FastAPI endpoints.

    Yields:
        AsyncSession: Database session that automatically handles cleanup
    """
    async with AsyncSessionLocal() as session:
        yield session
