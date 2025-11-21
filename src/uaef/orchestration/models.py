"""
UAEF Agent Orchestration Models

Database models for agents, workflows, tasks, and policies.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uaef.core.database import Base, TimestampMixin, UUIDMixin


class AgentStatus(str, Enum):
    """Status of an autonomous agent."""

    REGISTERED = "registered"
    ACTIVE = "active"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    DEACTIVATED = "deactivated"


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Status of a task within a workflow."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class Agent(Base, UUIDMixin, TimestampMixin):
    """
    Registered autonomous agent.

    Agents are the execution units that perform tasks within workflows.
    """

    __tablename__ = "agents"

    # Agent identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    agent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="claude",
    )  # claude, custom, external

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AgentStatus.REGISTERED,
    )

    # Capabilities and configuration
    capabilities: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Model configuration (for Claude agents)
    model: Mapped[str | None] = mapped_column(String(50))
    system_prompt: Mapped[str | None] = mapped_column(Text)
    tools: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # Metrics
    total_tasks: Mapped[int] = mapped_column(default=0)
    successful_tasks: Mapped[int] = mapped_column(default=0)
    failed_tasks: Mapped[int] = mapped_column(default=0)

    # Authentication
    api_key_hash: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_agents_status", "status"),
        Index("ix_agents_type", "agent_type"),
    )


class WorkflowDefinition(Base, UUIDMixin, TimestampMixin):
    """
    Workflow template definition.

    Defines the structure and tasks of a workflow that can be executed.
    """

    __tablename__ = "workflow_definitions"

    # Workflow identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")

    # DAG structure
    tasks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    edges: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )  # Task dependencies

    # Configuration
    input_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    default_config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Policies
    policies: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )  # Policy IDs to enforce

    # Metadata
    is_active: Mapped[bool] = mapped_column(default=True)
    tags: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )


class WorkflowExecution(Base, UUIDMixin, TimestampMixin):
    """
    Instance of a workflow execution.

    Tracks the state and progress of a running workflow.
    """

    __tablename__ = "workflow_executions"

    # Link to definition
    definition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflow_definitions.id"),
        nullable=False,
    )
    definition: Mapped[WorkflowDefinition] = relationship()

    # Execution identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=WorkflowStatus.PENDING,
    )

    # Input/Output
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    context: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )  # Shared workflow context

    # Progress tracking
    current_task_id: Mapped[str | None] = mapped_column(String(36))
    completed_tasks: Mapped[int] = mapped_column(default=0)
    total_tasks: Mapped[int] = mapped_column(default=0)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(default=0)

    # Initiator
    initiated_by: Mapped[str | None] = mapped_column(String(36))
    initiated_by_type: Mapped[str] = mapped_column(
        String(20),
        default="user",
    )  # user, agent, system, schedule

    __table_args__ = (
        Index("ix_workflow_executions_status", "status"),
        Index("ix_workflow_executions_definition", "definition_id"),
    )


class TaskExecution(Base, UUIDMixin, TimestampMixin):
    """
    Instance of a task execution within a workflow.

    Tracks the state of individual tasks.
    """

    __tablename__ = "task_executions"

    # Link to workflow
    workflow_execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflow_executions.id"),
        nullable=False,
    )
    workflow_execution: Mapped[WorkflowExecution] = relationship()

    # Task identification
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # agent, decision, human_approval, parallel, condition

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskStatus.PENDING,
    )

    # Agent assignment
    agent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
    )
    agent: Mapped[Agent | None] = relationship()

    # Input/Output
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Execution details
    prompt: Mapped[str | None] = mapped_column(Text)
    response: Mapped[str | None] = mapped_column(Text)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(default=0)

    # Dependencies
    depends_on: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )  # Task IDs this task depends on

    __table_args__ = (
        Index("ix_task_executions_workflow", "workflow_execution_id"),
        Index("ix_task_executions_status", "status"),
        Index("ix_task_executions_agent", "agent_id"),
    )


class Policy(Base, UUIDMixin, TimestampMixin):
    """
    Policy definition for workflow governance.

    Policies define rules that must be satisfied during workflow execution.
    """

    __tablename__ = "policies"

    # Policy identification
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    # Policy type
    policy_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # approval, rate_limit, data_access, compliance

    # Rules
    rules: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # Enforcement
    enforcement_level: Mapped[str] = mapped_column(
        String(20),
        default="strict",
    )  # strict, warn, log
    is_active: Mapped[bool] = mapped_column(default=True)

    # Scope
    applies_to_agents: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )  # Empty = all agents
    applies_to_workflows: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )  # Empty = all workflows


class HumanApproval(Base, UUIDMixin, TimestampMixin):
    """
    Human approval request for workflow tasks.

    Tracks approval requests and responses for human-in-the-loop workflows.
    """

    __tablename__ = "human_approvals"

    # Link to task
    task_execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("task_executions.id"),
        nullable=False,
    )
    task_execution: Mapped[TaskExecution] = relationship()

    # Request details
    request_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # approve_action, review_output, provide_input
    description: Mapped[str] = mapped_column(Text, nullable=False)
    context_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )  # pending, approved, rejected, expired

    # Response
    responded_by: Mapped[str | None] = mapped_column(String(36))
    responded_at: Mapped[datetime | None] = mapped_column()
    response_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    response_notes: Mapped[str | None] = mapped_column(Text)

    # Timeout
    expires_at: Mapped[datetime | None] = mapped_column()

    __table_args__ = (
        Index("ix_human_approvals_task", "task_execution_id"),
        Index("ix_human_approvals_status", "status"),
    )
