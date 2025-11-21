"""
UAEF Trust Ledger Models

Database models for the immutable audit trail, compliance checkpoints,
and verification chain.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uaef.core.database import Base, TimestampMixin, UUIDMixin


class EventType(str, Enum):
    """Types of events recorded in the trust ledger."""

    # Workflow events
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"

    # Task events
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRIED = "task_retried"

    # Agent events
    AGENT_REGISTERED = "agent_registered"
    AGENT_INVOKED = "agent_invoked"
    AGENT_RESPONSE = "agent_response"
    AGENT_ERROR = "agent_error"

    # Decision events
    DECISION_MADE = "decision_made"
    HUMAN_APPROVAL = "human_approval"
    HUMAN_REJECTION = "human_rejection"

    # Compliance events
    CHECKPOINT_PASSED = "checkpoint_passed"
    CHECKPOINT_FAILED = "checkpoint_failed"
    POLICY_VIOLATION = "policy_violation"

    # Settlement events
    SETTLEMENT_TRIGGERED = "settlement_triggered"
    SETTLEMENT_COMPLETED = "settlement_completed"
    SETTLEMENT_FAILED = "settlement_failed"

    # System events
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_CHANGED = "configuration_changed"


class CheckpointStatus(str, Enum):
    """Status of compliance checkpoints."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    REQUIRES_REVIEW = "requires_review"


class LedgerEvent(Base, UUIDMixin, TimestampMixin):
    """
    Immutable event record in the trust ledger.

    Each event is cryptographically linked to the previous event
    to form a verifiable chain.
    """

    __tablename__ = "ledger_events"

    # Event identification
    sequence_number: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Context
    workflow_id: Mapped[str | None] = mapped_column(
        String(36),
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(
        String(36),
        index=True,
    )
    agent_id: Mapped[str | None] = mapped_column(
        String(36),
        index=True,
    )

    # Event data
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Actor who triggered the event
    actor_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="system",
    )  # system, agent, user
    actor_id: Mapped[str | None] = mapped_column(String(36))

    # Hash chain for integrity verification
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    # Optional signature for non-repudiation
    signature: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_ledger_events_workflow_created", "workflow_id", "created_at"),
        Index("ix_ledger_events_type_created", "event_type", "created_at"),
    )


class ComplianceCheckpoint(Base, UUIDMixin, TimestampMixin):
    """
    Compliance checkpoint for workflow verification.

    Checkpoints validate that workflows meet required conditions
    at specified points in execution.
    """

    __tablename__ = "compliance_checkpoints"

    # Checkpoint identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Context
    workflow_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(String(36))

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CheckpointStatus.PENDING,
    )

    # Verification data
    rule_definition: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    verification_result: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Timestamps
    verified_at: Mapped[datetime | None] = mapped_column()

    # Link to ledger event
    ledger_event_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ledger_events.id"),
    )
    ledger_event: Mapped[LedgerEvent | None] = relationship()

    __table_args__ = (
        Index("ix_checkpoints_workflow_status", "workflow_id", "status"),
    )


class AuditTrail(Base, UUIDMixin, TimestampMixin):
    """
    High-level audit trail for compliance reporting.

    Aggregates related events for easier querying and reporting.
    """

    __tablename__ = "audit_trails"

    # Trail identification
    workflow_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    workflow_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Summary
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="in_progress",
    )
    total_events: Mapped[int] = mapped_column(default=0)
    total_checkpoints: Mapped[int] = mapped_column(default=0)
    passed_checkpoints: Mapped[int] = mapped_column(default=0)
    failed_checkpoints: Mapped[int] = mapped_column(default=0)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()

    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    workflow_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Hash of final state for verification
    final_hash: Mapped[str | None] = mapped_column(String(64))


class LedgerBlock(Base, UUIDMixin, TimestampMixin):
    """
    Block of events for batch verification.

    Groups multiple events together with a single block hash
    for more efficient verification of large event sequences.
    """

    __tablename__ = "ledger_blocks"

    # Block identification
    block_number: Mapped[int] = mapped_column(
        nullable=False,
        unique=True,
    )

    # Event range
    start_sequence: Mapped[int] = mapped_column(nullable=False)
    end_sequence: Mapped[int] = mapped_column(nullable=False)
    event_count: Mapped[int] = mapped_column(nullable=False)

    # Hash chain
    previous_block_hash: Mapped[str | None] = mapped_column(String(64))
    block_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    # Merkle root of all events in block
    merkle_root: Mapped[str] = mapped_column(String(64), nullable=False)

    # Block timestamp
    finalized_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
