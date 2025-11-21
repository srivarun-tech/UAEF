"""
UAEF Test Fixtures

Shared fixtures for all test modules.
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from uaef.core.config import Settings
from uaef.core.database import Base

# Use SQLite for testing by default
TEST_DATABASE_URL = os.environ.get(
    "UAEF_TEST_DB_URL",
    "sqlite+aiosqlite:///:memory:",
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests with automatic rollback."""
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with test values."""
    return Settings(
        environment="test",
        database={"url": TEST_DATABASE_URL},
        agent={"anthropic_api_key": "test-key"},
        security={"jwt_secret": "test-secret-key-for-testing-only"},
    )


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for agent tests."""
    with patch("anthropic.Anthropic") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client

        # Configure default response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Test response")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.stop_reason = "end_turn"

        mock_client.messages.create.return_value = mock_response

        yield mock_client


@pytest.fixture
def sample_workflow_data() -> dict:
    """Sample workflow definition data for tests."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "version": "1.0.0",
        "tasks": [
            {
                "id": "task-1",
                "name": "First Task",
                "type": "agent",
                "config": {"prompt": "Do something"},
            },
            {
                "id": "task-2",
                "name": "Second Task",
                "type": "agent",
                "config": {"prompt": "Do something else"},
            },
        ],
        "edges": [
            {"from": "task-1", "to": "task-2"},
        ],
    }


@pytest.fixture
def sample_agent_data() -> dict:
    """Sample agent registration data for tests."""
    return {
        "name": "Test Agent",
        "description": "A test agent",
        "agent_type": "claude",
        "capabilities": ["read", "write", "analyze"],
        "model": "claude-sonnet-4-20250514",
        "system_prompt": "You are a helpful test agent.",
    }
