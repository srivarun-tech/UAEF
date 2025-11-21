"""
UAEF Settlement Models

Database models for financial settlement signals and rules.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import DECIMAL, JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uaef.core.database import Base, TimestampMixin, UUIDMixin


class SettlementStatus(str, Enum):
    """Status of a settlement signal."""

    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecipientType(str, Enum):
    """Type of settlement recipient."""

    AGENT = "agent"
    USER = "user"
    EXTERNAL = "external"
    POOL = "pool"  # Settlement pool for distribution


class SettlementRule(Base, UUIDMixin, TimestampMixin):
    """
    Settlement rule definition.

    Defines when and how settlements are triggered for workflows.
    """

    __tablename__ = "settlement_rules"

    # Rule identification
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    # Scope
    workflow_definition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("workflow_definitions.id"),
    )

    # Trigger conditions (JSON expression)
    trigger_conditions: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Amount calculation
    amount_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="fixed",
    )  # fixed, variable, calculated
    fixed_amount: Mapped[Decimal | None] = mapped_column(
        DECIMAL(precision=18, scale=2),
    )
    amount_formula: Mapped[str | None] = mapped_column(
        Text,
        comment="Python expression for calculated amounts",
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Recipient
    recipient_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RecipientType.AGENT,
    )
    fixed_recipient_id: Mapped[str | None] = mapped_column(String(36))
    recipient_selector: Mapped[str | None] = mapped_column(
        Text,
        comment="Expression to select recipient dynamically",
    )

    # Approval requirements
    requires_approval: Mapped[bool] = mapped_column(default=False)
    approval_threshold: Mapped[Decimal | None] = mapped_column(
        DECIMAL(precision=18, scale=2),
    )

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)

    # Rule metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    rule_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )


class SettlementSignal(Base, UUIDMixin, TimestampMixin):
    """
    Settlement signal generated from workflow completion.

    Represents a financial settlement to be processed.
    """

    __tablename__ = "settlement_signals"

    # Link to workflow
    workflow_execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflow_executions.id"),
        nullable=False,
    )

    # Link to rule
    settlement_rule_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("settlement_rules.id"),
    )
    settlement_rule: Mapped[SettlementRule | None] = relationship()

    # Amount
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=18, scale=2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Recipient
    recipient_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    recipient_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SettlementStatus.PENDING,
    )

    # Approval
    approved_by: Mapped[str | None] = mapped_column(String(36))
    approved_at: Mapped[datetime | None] = mapped_column()

    # Processing
    processed_at: Mapped[datetime | None] = mapped_column()
    transaction_id: Mapped[str | None] = mapped_column(
        String(100),
        comment="External payment system transaction ID",
    )

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(default=0)

    # Signal metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    signal_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    __table_args__ = (
        Index("ix_settlement_signals_workflow", "workflow_execution_id"),
        Index("ix_settlement_signals_status", "status"),
        Index("ix_settlement_signals_recipient", "recipient_id"),
    )
