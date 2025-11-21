"""
UAEF Logging and Observability

Structured logging with context propagation for distributed
tracing across agent workflows.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from uaef.core.config import get_settings


def configure_logging() -> None:
    """Configure structured logging for UAEF."""
    settings = get_settings()

    # Shared processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.environment == "development":
        # Pretty console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # JSON output for production (CloudWatch, etc.)
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding temporary log context."""

    def __init__(self, **kwargs: Any):
        self._context = kwargs
        self._tokens: list[Any] = []

    def __enter__(self) -> "LogContext":
        for key, value in self._context.items():
            token = structlog.contextvars.bind_contextvars(**{key: value})
            self._tokens.append((key, token))
        return self

    def __exit__(self, *args: Any) -> None:
        structlog.contextvars.unbind_contextvars(
            *[key for key, _ in self._tokens]
        )


def bind_workflow_context(
    workflow_id: str,
    workflow_name: str | None = None,
) -> None:
    """Bind workflow context to all subsequent log entries."""
    structlog.contextvars.bind_contextvars(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
    )


def bind_agent_context(
    agent_id: str,
    agent_type: str | None = None,
) -> None:
    """Bind agent context to all subsequent log entries."""
    structlog.contextvars.bind_contextvars(
        agent_id=agent_id,
        agent_type=agent_type,
    )


def bind_task_context(
    task_id: str,
    task_name: str | None = None,
) -> None:
    """Bind task context to all subsequent log entries."""
    structlog.contextvars.bind_contextvars(
        task_id=task_id,
        task_name=task_name,
    )


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


# Event logging helpers for common UAEF events
class UAEFEvents:
    """Standard event logging for UAEF operations."""

    def __init__(self):
        self.logger = get_logger("uaef.events")

    def workflow_started(self, workflow_id: str, name: str, **kwargs: Any) -> None:
        self.logger.info(
            "workflow_started",
            workflow_id=workflow_id,
            workflow_name=name,
            **kwargs,
        )

    def workflow_completed(self, workflow_id: str, status: str, **kwargs: Any) -> None:
        self.logger.info(
            "workflow_completed",
            workflow_id=workflow_id,
            status=status,
            **kwargs,
        )

    def task_started(self, task_id: str, agent_id: str, **kwargs: Any) -> None:
        self.logger.info(
            "task_started",
            task_id=task_id,
            agent_id=agent_id,
            **kwargs,
        )

    def task_completed(self, task_id: str, result: str, **kwargs: Any) -> None:
        self.logger.info(
            "task_completed",
            task_id=task_id,
            result=result,
            **kwargs,
        )

    def ledger_event_recorded(self, event_id: str, event_type: str, **kwargs: Any) -> None:
        self.logger.info(
            "ledger_event_recorded",
            event_id=event_id,
            event_type=event_type,
            **kwargs,
        )

    def settlement_triggered(self, settlement_id: str, amount: float, **kwargs: Any) -> None:
        self.logger.info(
            "settlement_triggered",
            settlement_id=settlement_id,
            amount=amount,
            **kwargs,
        )

    def compliance_checkpoint(
        self, checkpoint_id: str, status: str, **kwargs: Any
    ) -> None:
        self.logger.info(
            "compliance_checkpoint",
            checkpoint_id=checkpoint_id,
            status=status,
            **kwargs,
        )
