"""
UAEF Agent Integration Module

Platform-agnostic agent coordination, execution, and reputation tracking.
Supports agents from LangChain, AutoGPT, CrewAI, Temporal, and custom platforms.
"""

from uaef.agents.agents import AgentRegistry, ClaudeAgentExecutor
from uaef.agents.models import (
    Agent,
    AgentExecution,
    AgentPlatform,
    AgentReputation,
    AgentStatus,
    ExecutionStatus,
    HumanApproval,
    Policy,
    TaskExecution,
    TaskStatus,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStatus,
)
from uaef.agents.workflow import TaskScheduler, WorkflowService

__all__ = [
    # Platform Models
    "AgentPlatform",
    "ExecutionStatus",
    # Core Models
    "Agent",
    "AgentStatus",
    "AgentExecution",
    "AgentReputation",
    "WorkflowDefinition",
    "WorkflowExecution",
    "WorkflowStatus",
    "TaskExecution",
    "TaskStatus",
    "Policy",
    "HumanApproval",
    # Services
    "AgentRegistry",
    "ClaudeAgentExecutor",
    "WorkflowService",
    "TaskScheduler",
]
