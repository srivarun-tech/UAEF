"""
UAEF Database Layer

SQLAlchemy async database setup with connection pooling optimized
for serverless environments.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

from sqlalchemy import MetaData, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from uaef.core.config import get_settings

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all UAEF models."""

    metadata = MetaData(naming_convention=convention)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin for UUID primary key."""

    id: Mapped[str] = mapped_column(
        primary_key=True,
        default=lambda: str(uuid4()),
    )


def get_async_engine():
    """Create async database engine with serverless-optimized pooling."""
    settings = get_settings()

    # Convert postgresql:// to postgresql+asyncpg://
    db_url = str(settings.database.url)
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return create_async_engine(
        db_url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_recycle=settings.database.pool_recycle,
        echo=settings.database.echo,
        # Serverless optimization: pre-ping to handle stale connections
        pool_pre_ping=True,
    )


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    engine = get_async_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# Global session maker
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create global session maker."""
    global _session_maker
    if _session_maker is None:
        _session_maker = get_async_session_maker()
    return _session_maker


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session as async context manager."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database tables."""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global _session_maker
    if _session_maker is not None:
        # Get the engine from the session maker and dispose it
        engine = get_async_engine()
        await engine.dispose()
        _session_maker = None
