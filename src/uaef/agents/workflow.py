"""
UAEF Workflow Service

Core workflow orchestration engine for executing workflows with task scheduling,
dependency resolution, and policy enforcement.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uaef.core.logging import get_logger
from uaef.ledger import EventType, LedgerEventService
from uaef.agents.agents import AgentRegistry, ClaudeAgentExecutor
from uaef.agents.models import (
    Agent,
    AgentStatus,
    HumanApproval,
    Policy,
    TaskExecution,
    TaskStatus,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStatus,
)
from uaef.settlement import SettlementService

logger = get_logger(__name__)


class WorkflowService:
    """Service for managing workflow execution lifecycle."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_service = LedgerEventService(session)
        self.agent_registry = AgentRegistry(session)
        self.agent_executor = ClaudeAgentExecutor(session)
        self.settlement_service = SettlementService(session)

    async def create_definition(
        self,
        name: str,
        tasks: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        description: str | None = None,
        version: str = "1.0.0",
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        default_config: dict[str, Any] | None = None,
        policies: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> WorkflowDefinition:
        """Create a new workflow definition."""
        definition = WorkflowDefinition(
            name=name,
            description=description,
            version=version,
            tasks=tasks,
            edges=edges,
            input_schema=input_schema,
            output_schema=output_schema,
            default_config=default_config or {},
            policies=policies or [],
            tags=tags or [],
        )

        self.session.add(definition)
        await self.session.flush()

        logger.info(
            "workflow_definition_created",
            definition_id=definition.id,
            name=name,
            task_count=len(tasks),
        )

        return definition

    async def get_definition(self, definition_id: str) -> WorkflowDefinition | None:
        """Get a workflow definition by ID."""
        result = await self.session.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.id == definition_id)
        )
        return result.scalar_one_or_none()

    async def start_workflow(
        self,
        definition_id: str,
        input_data: dict[str, Any],
        name: str | None = None,
        initiated_by: str | None = None,
        initiated_by_type: str = "user",
    ) -> WorkflowExecution:
        """Start a new workflow execution."""
        definition = await self.get_definition(definition_id)
        if not definition:
            raise ValueError(f"Workflow definition {definition_id} not found")

        if not definition.is_active:
            raise ValueError(f"Workflow definition {definition_id} is not active")

        # Create workflow execution
        execution = WorkflowExecution(
            definition_id=definition_id,
            name=name or definition.name,
            status=WorkflowStatus.RUNNING.value,
            input_data=input_data,
            context={},
            total_tasks=len(definition.tasks),
            started_at=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            initiated_by_type=initiated_by_type,
        )

        self.session.add(execution)
        await self.session.flush()

        # Record workflow start event
        await self.event_service.record_event(
            event_type=EventType.WORKFLOW_STARTED,
            payload={
                "workflow_name": execution.name,
                "definition_id": definition_id,
                "task_count": len(definition.tasks),
            },
            workflow_id=execution.id,
        )

        logger.info(
            "workflow_started",
            execution_id=execution.id,
            definition_id=definition_id,
        )

        # Create task executions
        await self._create_task_executions(execution, definition)

        # Execute initial tasks
        await self.execute_next_tasks(execution.id)

        return execution

    async def _create_task_executions(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition,
    ) -> None:
        """Create task execution records for all tasks in the workflow."""
        # Build dependency map from edges
        dependency_map: dict[str, list[str]] = {}
        for edge in definition.edges:
            from_task = edge.get("from")
            to_task = edge.get("to")
            if to_task:
                if to_task not in dependency_map:
                    dependency_map[to_task] = []
                if from_task:
                    dependency_map[to_task].append(from_task)

        # Create task executions
        task_id_map: dict[str, str] = {}  # Map task definition ID to execution ID

        for task_def in definition.tasks:
            task_id = task_def.get("id")
            task_name = task_def.get("name", task_id)
            task_type = task_def.get("type", "agent")

            # Get dependencies using the definition task IDs
            depends_on_def_ids = dependency_map.get(task_id, [])

            task_exec = TaskExecution(
                workflow_execution_id=execution.id,
                task_name=task_name,
                task_type=task_type,
                status=TaskStatus.PENDING.value,
                input_data=task_def.get("config", {}),
                depends_on=depends_on_def_ids,  # Store definition IDs for now
            )

            self.session.add(task_exec)
            await self.session.flush()

            # Map definition ID to execution ID
            task_id_map[task_id] = task_exec.id

        # Update depends_on with execution IDs
        result = await self.session.execute(
            select(TaskExecution).where(
                TaskExecution.workflow_execution_id == execution.id
            )
        )
        all_tasks = list(result.scalars().all())

        # Create reverse map: task name -> execution ID
        name_to_exec_id = {task.task_name: task.id for task in all_tasks}

        # For each task, find matching task names in depends_on and map to execution IDs
        for task in all_tasks:
            if task.depends_on:
                # Find tasks in definition to get their names
                exec_id_depends = []
                for def_id in task.depends_on:
                    if def_id in task_id_map:
                        exec_id_depends.append(task_id_map[def_id])
                task.depends_on = exec_id_depends

        await self.session.flush()

    async def execute_next_tasks(self, execution_id: str) -> list[TaskExecution]:
        """Execute all ready tasks (tasks with satisfied dependencies)."""
        scheduler = TaskScheduler(self.session)
        ready_tasks = await scheduler.get_ready_tasks(execution_id)

        executed_tasks = []
        for task in ready_tasks:
            try:
                await self._execute_task(task)
                executed_tasks.append(task)
            except Exception as e:
                logger.error(
                    "task_execution_failed",
                    task_id=task.id,
                    error=str(e),
                )
                await self._handle_task_failure(task, str(e))

        return executed_tasks

    async def _execute_task(self, task: TaskExecution) -> None:
        """Execute a single task."""
        # Update task status
        task.status = TaskStatus.RUNNING.value
        task.started_at = datetime.now(timezone.utc)
        await self.session.flush()

        # Record task start event
        await self.event_service.record_event(
            event_type=EventType.TASK_STARTED,
            payload={
                "task_name": task.task_name,
                "task_type": task.task_type,
            },
            workflow_id=task.workflow_execution_id,
            task_id=task.id,
        )

        # Execute based on task type
        if task.task_type == "agent":
            await self._execute_agent_task(task)
        elif task.task_type == "human_approval":
            await self._execute_human_approval_task(task)
        elif task.task_type == "decision":
            await self._execute_decision_task(task)
        elif task.task_type == "parallel":
            await self._execute_parallel_task(task)
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")

    async def _execute_agent_task(self, task: TaskExecution) -> None:
        """Execute an agent task."""
        # Find an available agent
        capability = task.input_data.get("capability")
        agent = await self.agent_registry.find_available_agent(capability=capability)

        if not agent:
            raise ValueError(f"No available agent found for capability: {capability}")

        # Assign agent to task
        task.agent_id = agent.id
        await self.session.flush()

        # Build prompt from task config
        prompt_template = task.input_data.get("prompt", "")
        context = task.input_data.get("context", {})

        # Get workflow execution for context
        execution = await self._get_execution(task.workflow_execution_id)
        context.update(execution.context)

        # Invoke agent
        result = await self.agent_executor.invoke(
            agent=agent,
            prompt=prompt_template,
            context=context,
            workflow_id=task.workflow_execution_id,
            task_id=task.id,
        )

        # Complete task with result
        await self.complete_task(
            task_id=task.id,
            output_data={"result": result["content"], "usage": result.get("usage")},
        )

    async def _execute_human_approval_task(self, task: TaskExecution) -> None:
        """Execute a human approval task."""
        # Create approval request
        approval = HumanApproval(
            task_execution_id=task.id,
            request_type="approve_action",
            description=task.input_data.get("description", "Approval required"),
            context_data=task.input_data.get("context", {}),
            status="pending",
        )

        self.session.add(approval)
        await self.session.flush()

        # Update task to waiting
        task.status = TaskStatus.WAITING_INPUT.value
        await self.session.flush()

        logger.info(
            "human_approval_requested",
            task_id=task.id,
            approval_id=approval.id,
        )

    async def _execute_decision_task(self, task: TaskExecution) -> None:
        """Execute a decision task."""
        # Simple decision based on input conditions
        conditions = task.input_data.get("conditions", {})
        execution = await self._get_execution(task.workflow_execution_id)

        # Evaluate conditions against context
        decision = self._evaluate_conditions(conditions, execution.context)

        await self.complete_task(
            task_id=task.id,
            output_data={"decision": decision},
        )

    def _evaluate_conditions(
        self,
        conditions: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Evaluate simple conditions."""
        for key, expected in conditions.items():
            actual = context.get(key)
            if actual != expected:
                return False
        return True

    async def _execute_parallel_task(self, task: TaskExecution) -> None:
        """Execute a parallel task container."""
        # For now, just complete immediately
        # In real implementation, would spawn parallel sub-tasks
        await self.complete_task(
            task_id=task.id,
            output_data={"status": "parallel_execution_started"},
        )

    async def complete_task(
        self,
        task_id: str,
        output_data: dict[str, Any],
    ) -> None:
        """Complete a task successfully."""
        task = await self._get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.now(timezone.utc)
        task.output_data = output_data
        await self.session.flush()

        # Record task completion event
        await self.event_service.record_event(
            event_type=EventType.TASK_COMPLETED,
            payload={
                "task_name": task.task_name,
                "output_keys": list(output_data.keys()),
            },
            workflow_id=task.workflow_execution_id,
            task_id=task.id,
        )

        # Update agent metrics if agent was assigned
        if task.agent_id:
            await self.agent_registry.update_agent_metrics(task.agent_id, success=True)

        # Update workflow progress
        execution = await self._get_execution(task.workflow_execution_id)
        execution.completed_tasks += 1
        await self.session.flush()

        logger.info(
            "task_completed",
            task_id=task_id,
            workflow_id=task.workflow_execution_id,
        )

        # Check if workflow is complete
        if execution.completed_tasks >= execution.total_tasks:
            await self._complete_workflow(execution)
        else:
            # Execute next ready tasks
            await self.execute_next_tasks(execution.id)

    async def _handle_task_failure(self, task: TaskExecution, error_message: str) -> None:
        """Handle task failure with retry logic."""
        task.error_message = error_message
        task.retry_count += 1

        # Check if should retry
        max_retries = 3
        if task.retry_count < max_retries:
            task.status = TaskStatus.PENDING.value
            await self.session.flush()

            await self.event_service.record_event(
                event_type=EventType.TASK_RETRIED,
                payload={
                    "task_name": task.task_name,
                    "retry_count": task.retry_count,
                    "error": error_message,
                },
                workflow_id=task.workflow_execution_id,
                task_id=task.id,
            )

            logger.info(
                "task_retrying",
                task_id=task.id,
                retry_count=task.retry_count,
            )
        else:
            task.status = TaskStatus.FAILED.value
            task.completed_at = datetime.now(timezone.utc)
            await self.session.flush()

            await self.event_service.record_event(
                event_type=EventType.TASK_FAILED,
                payload={
                    "task_name": task.task_name,
                    "error": error_message,
                    "retry_count": task.retry_count,
                },
                workflow_id=task.workflow_execution_id,
                task_id=task.id,
            )

            # Update agent metrics if agent was assigned
            if task.agent_id:
                await self.agent_registry.update_agent_metrics(
                    task.agent_id, success=False
                )

            # Fail the workflow
            execution = await self._get_execution(task.workflow_execution_id)
            await self._fail_workflow(execution, f"Task {task.task_name} failed: {error_message}")

    async def _complete_workflow(self, execution: WorkflowExecution) -> None:
        """Complete a workflow successfully."""
        execution.status = WorkflowStatus.COMPLETED.value
        execution.completed_at = datetime.now(timezone.utc)
        await self.session.flush()

        await self.event_service.record_event(
            event_type=EventType.WORKFLOW_COMPLETED,
            payload={
                "workflow_name": execution.name,
                "completed_tasks": execution.completed_tasks,
            },
            workflow_id=execution.id,
        )

        logger.info(
            "workflow_completed",
            execution_id=execution.id,
        )

        # Trigger settlement evaluation
        await self._trigger_settlement(execution)

    async def _fail_workflow(self, execution: WorkflowExecution, error_message: str) -> None:
        """Fail a workflow."""
        execution.status = WorkflowStatus.FAILED.value
        execution.completed_at = datetime.now(timezone.utc)
        execution.error_message = error_message
        await self.session.flush()

        await self.event_service.record_event(
            event_type=EventType.WORKFLOW_FAILED,
            payload={
                "workflow_name": execution.name,
                "error": error_message,
            },
            workflow_id=execution.id,
        )

        logger.error(
            "workflow_failed",
            execution_id=execution.id,
            error=error_message,
        )

    async def _trigger_settlement(self, execution: WorkflowExecution) -> None:
        """Trigger settlement evaluation after workflow completion."""
        try:
            definition = await self.get_definition(execution.definition_id)

            workflow_data = {
                "definition_id": execution.definition_id,
                "status": execution.status,
                "completed_tasks": execution.completed_tasks,
                **execution.context,
                **(execution.output_data or {}),
            }

            signals = await self.settlement_service.evaluate_triggers(
                workflow_execution_id=execution.id,
                workflow_data=workflow_data,
            )

            logger.info(
                "settlement_triggered",
                execution_id=execution.id,
                signal_count=len(signals),
            )
        except Exception as e:
            logger.error(
                "settlement_trigger_failed",
                execution_id=execution.id,
                error=str(e),
            )

    async def _get_execution(self, execution_id: str) -> WorkflowExecution:
        """Get workflow execution by ID."""
        result = await self.session.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise ValueError(f"Workflow execution {execution_id} not found")
        return execution

    async def _get_task(self, task_id: str) -> TaskExecution | None:
        """Get task execution by ID."""
        result = await self.session.execute(
            select(TaskExecution).where(TaskExecution.id == task_id)
        )
        return result.scalar_one_or_none()


class TaskScheduler:
    """Scheduler for determining which tasks are ready to execute."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_ready_tasks(self, execution_id: str) -> list[TaskExecution]:
        """Get all tasks that are ready to execute (dependencies satisfied)."""
        # Get all pending tasks
        result = await self.session.execute(
            select(TaskExecution).where(
                TaskExecution.workflow_execution_id == execution_id,
                TaskExecution.status == TaskStatus.PENDING.value,
            )
        )
        pending_tasks = list(result.scalars().all())

        ready_tasks = []
        for task in pending_tasks:
            if await self.resolve_dependencies(task):
                ready_tasks.append(task)

        return ready_tasks

    async def resolve_dependencies(self, task: TaskExecution) -> bool:
        """Check if all dependencies for a task are satisfied."""
        if not task.depends_on:
            return True

        # Check if all dependent tasks are completed
        result = await self.session.execute(
            select(TaskExecution).where(
                TaskExecution.id.in_(task.depends_on),
                TaskExecution.workflow_execution_id == task.workflow_execution_id,
            )
        )
        dependent_tasks = list(result.scalars().all())

        if len(dependent_tasks) != len(task.depends_on):
            # Some dependent tasks don't exist
            return False

        for dep_task in dependent_tasks:
            if dep_task.status != TaskStatus.COMPLETED.value:
                return False

        return True
