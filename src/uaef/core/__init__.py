"""
UAEF Core Module

Foundational components for configuration, database, security, and logging.
"""

from uaef.core.config import Settings, get_settings
from uaef.core.database import Base, TimestampMixin, UUIDMixin, get_session, init_db
from uaef.core.logging import (
    LogContext,
    UAEFEvents,
    bind_agent_context,
    bind_task_context,
    bind_workflow_context,
    configure_logging,
    get_logger,
)
from uaef.core.security import (
    EncryptionService,
    HashService,
    TokenManager,
    generate_api_key,
    generate_event_id,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Database
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "get_session",
    "init_db",
    # Logging
    "configure_logging",
    "get_logger",
    "LogContext",
    "UAEFEvents",
    "bind_workflow_context",
    "bind_agent_context",
    "bind_task_context",
    # Security
    "TokenManager",
    "EncryptionService",
    "HashService",
    "generate_api_key",
    "generate_event_id",
]
