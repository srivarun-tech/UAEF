"""Add settlement tables.

Revision ID: 002_settlement
Revises: 001_initial
Create Date: 2025-01-19

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import DECIMAL

# revision identifiers, used by Alembic.
revision: str = "002_settlement"
down_revision: str | None = "001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Settlement rules table
    op.create_table(
        "settlement_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "workflow_definition_id",
            sa.String(36),
            sa.ForeignKey("workflow_definitions.id"),
            nullable=True,
        ),
        sa.Column("trigger_conditions", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("amount_type", sa.String(20), nullable=False, server_default="fixed"),
        sa.Column("fixed_amount", DECIMAL(precision=18, scale=2), nullable=True),
        sa.Column("amount_formula", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("recipient_type", sa.String(20), nullable=False, server_default="agent"),
        sa.Column("fixed_recipient_id", sa.String(36), nullable=True),
        sa.Column("recipient_selector", sa.Text(), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("approval_threshold", DECIMAL(precision=18, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("rule_metadata", sa.JSON(), nullable=False, server_default="{}"),
    )

    # Settlement signals table
    op.create_table(
        "settlement_signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "workflow_execution_id",
            sa.String(36),
            sa.ForeignKey("workflow_executions.id"),
            nullable=False,
        ),
        sa.Column(
            "settlement_rule_id",
            sa.String(36),
            sa.ForeignKey("settlement_rules.id"),
            nullable=True,
        ),
        sa.Column("amount", DECIMAL(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("recipient_type", sa.String(20), nullable=False),
        sa.Column("recipient_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("transaction_id", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signal_metadata", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_settlement_signals_workflow",
        "settlement_signals",
        ["workflow_execution_id"],
    )
    op.create_index("ix_settlement_signals_status", "settlement_signals", ["status"])
    op.create_index(
        "ix_settlement_signals_recipient",
        "settlement_signals",
        ["recipient_id"],
    )


def downgrade() -> None:
    op.drop_table("settlement_signals")
    op.drop_table("settlement_rules")
