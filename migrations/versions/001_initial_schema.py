"""Initial schema with all models.

Revision ID: 001_initial
Revises:
Create Date: 2025-01-19

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("agent_type", sa.String(50), nullable=False, server_default="claude"),
        sa.Column("status", sa.String(20), nullable=False, server_default="registered"),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("configuration", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("model", sa.String(50), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("tools", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("total_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("api_key_hash", sa.String(64), nullable=True),
    )
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_index("ix_agents_type", "agents", ["agent_type"])

    # Ledger events table
    op.create_table(
        "ledger_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("workflow_id", sa.String(36), nullable=True, index=True),
        sa.Column("task_id", sa.String(36), nullable=True, index=True),
        sa.Column("agent_id", sa.String(36), nullable=True, index=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("actor_type", sa.String(20), nullable=False, server_default="system"),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("previous_hash", sa.String(64), nullable=True),
        sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("signature", sa.Text(), nullable=True),
    )
    op.create_index("ix_ledger_events_workflow_created", "ledger_events", ["workflow_id", "created_at"])
    op.create_index("ix_ledger_events_type_created", "ledger_events", ["event_type", "created_at"])

    # Compliance checkpoints table
    op.create_table(
        "compliance_checkpoints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("workflow_id", sa.String(36), nullable=False, index=True),
        sa.Column("task_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("rule_definition", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("verification_result", sa.JSON(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("ledger_event_id", sa.String(36), sa.ForeignKey("ledger_events.id"), nullable=True),
    )
    op.create_index("ix_checkpoints_workflow_status", "compliance_checkpoints", ["workflow_id", "status"])

    # Audit trails table
    op.create_table(
        "audit_trails",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("workflow_id", sa.String(36), nullable=False, index=True),
        sa.Column("workflow_name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("total_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_checkpoints", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_checkpoints", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_checkpoints", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("final_hash", sa.String(64), nullable=True),
    )

    # Ledger blocks table
    op.create_table(
        "ledger_blocks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("block_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("start_sequence", sa.Integer(), nullable=False),
        sa.Column("end_sequence", sa.Integer(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("previous_block_hash", sa.String(64), nullable=True),
        sa.Column("block_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("merkle_root", sa.String(64), nullable=False),
        sa.Column("finalized_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Workflow definitions table
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("tasks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("edges", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("input_schema", sa.JSON(), nullable=True),
        sa.Column("output_schema", sa.JSON(), nullable=True),
        sa.Column("default_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("policies", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
    )

    # Workflow executions table
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("definition_id", sa.String(36), sa.ForeignKey("workflow_definitions.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("context", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("current_task_id", sa.String(36), nullable=True),
        sa.Column("completed_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("initiated_by", sa.String(36), nullable=True),
        sa.Column("initiated_by_type", sa.String(20), nullable=False, server_default="user"),
    )
    op.create_index("ix_workflow_executions_status", "workflow_executions", ["status"])
    op.create_index("ix_workflow_executions_definition", "workflow_executions", ["definition_id"])

    # Task executions table
    op.create_table(
        "task_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("workflow_execution_id", sa.String(36), sa.ForeignKey("workflow_executions.id"), nullable=False),
        sa.Column("task_name", sa.String(100), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("input_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("depends_on", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_task_executions_workflow", "task_executions", ["workflow_execution_id"])
    op.create_index("ix_task_executions_status", "task_executions", ["status"])
    op.create_index("ix_task_executions_agent", "task_executions", ["agent_id"])

    # Policies table
    op.create_table(
        "policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("policy_type", sa.String(50), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("enforcement_level", sa.String(20), nullable=False, server_default="strict"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("applies_to_agents", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("applies_to_workflows", sa.JSON(), nullable=False, server_default="[]"),
    )

    # Human approvals table
    op.create_table(
        "human_approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("task_execution_id", sa.String(36), sa.ForeignKey("task_executions.id"), nullable=False),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("context_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("responded_by", sa.String(36), nullable=True),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("response_data", sa.JSON(), nullable=True),
        sa.Column("response_notes", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_human_approvals_task", "human_approvals", ["task_execution_id"])
    op.create_index("ix_human_approvals_status", "human_approvals", ["status"])


def downgrade() -> None:
    op.drop_table("human_approvals")
    op.drop_table("policies")
    op.drop_table("task_executions")
    op.drop_table("workflow_executions")
    op.drop_table("workflow_definitions")
    op.drop_table("ledger_blocks")
    op.drop_table("audit_trails")
    op.drop_table("compliance_checkpoints")
    op.drop_table("ledger_events")
    op.drop_table("agents")
