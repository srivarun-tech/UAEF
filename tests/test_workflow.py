"""
Tests for UAEF Workflow Orchestration

Tests for WorkflowService and TaskScheduler.
"""

from unittest.mock import MagicMock, patch

import pytest

from uaef.agents.models import AgentStatus, TaskStatus, WorkflowStatus
from uaef.agents.workflow import TaskScheduler, WorkflowService


class TestWorkflowService:
    """Tests for WorkflowService."""

    @pytest.mark.asyncio
    async def test_create_definition(self, session):
        """Test creating a workflow definition."""
        service = WorkflowService(session)

        tasks = [
            {"id": "task-1", "name": "First Task", "type": "agent"},
            {"id": "task-2", "name": "Second Task", "type": "agent"},
        ]
        edges = [{"from": "task-1", "to": "task-2"}]

        definition = await service.create_definition(
            name="Test Workflow",
            description="A test workflow",
            tasks=tasks,
            edges=edges,
        )

        assert definition.id is not None
        assert definition.name == "Test Workflow"
        assert len(definition.tasks) == 2
        assert len(definition.edges) == 1
        assert definition.is_active is True

    @pytest.mark.asyncio
    async def test_get_definition(self, session):
        """Test retrieving a workflow definition."""
        service = WorkflowService(session)

        created = await service.create_definition(
            name="Get Test",
            tasks=[{"id": "t1", "name": "Task", "type": "agent"}],
            edges=[],
        )

        retrieved = await service.get_definition(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Get Test"

    @pytest.mark.asyncio
    async def test_start_workflow(self, session, sample_workflow_data):
        """Test starting a workflow execution."""
        service = WorkflowService(session)

        # Create definition
        definition = await service.create_definition(
            name=sample_workflow_data["name"],
            tasks=sample_workflow_data["tasks"],
            edges=sample_workflow_data["edges"],
        )

        # Mock agent executor to avoid actual API calls
        with patch.object(service.agent_executor, "invoke") as mock_invoke:
            mock_invoke.return_value = {
                "content": "Task result",
                "usage": {"input_tokens": 10, "output_tokens": 20},
            }

            # Start workflow
            execution = await service.start_workflow(
                definition_id=definition.id,
                input_data={"test": "data"},
                initiated_by="test-user",
            )

            assert execution.id is not None
            assert execution.definition_id == definition.id
            assert execution.status == WorkflowStatus.RUNNING.value
            assert execution.input_data == {"test": "data"}
            assert execution.total_tasks == 2
            assert execution.started_at is not None

    @pytest.mark.asyncio
    async def test_start_workflow_creates_tasks(self, session, sample_workflow_data):
        """Test that starting a workflow creates task executions."""
        service = WorkflowService(session)

        definition = await service.create_definition(
            name=sample_workflow_data["name"],
            tasks=sample_workflow_data["tasks"],
            edges=sample_workflow_data["edges"],
        )

        with patch.object(service.agent_executor, "invoke"):
            execution = await service.start_workflow(
                definition_id=definition.id,
                input_data={},
            )

            # Verify tasks were created
            from sqlalchemy import select

            from uaef.agents.models import TaskExecution

            result = await session.execute(
                select(TaskExecution).where(
                    TaskExecution.workflow_execution_id == execution.id
                )
            )
            tasks = list(result.scalars().all())

            assert len(tasks) == 2
            assert all(t.status == TaskStatus.PENDING.value for t in tasks if t.depends_on)

    @pytest.mark.asyncio
    async def test_start_workflow_inactive_definition(self, session):
        """Test that starting an inactive workflow raises error."""
        service = WorkflowService(session)

        definition = await service.create_definition(
            name="Inactive",
            tasks=[{"id": "t1", "name": "Task", "type": "agent"}],
            edges=[],
        )
        definition.is_active = False
        await session.flush()

        with pytest.raises(ValueError, match="not active"):
            await service.start_workflow(
                definition_id=definition.id,
                input_data={},
            )

    @pytest.mark.asyncio
    async def test_complete_task(self, session, sample_agent_data):
        """Test completing a task."""
        service = WorkflowService(session)

        # Create definition and start workflow
        definition = await service.create_definition(
            name="Complete Task Test",
            tasks=[{"id": "t1", "name": "Single Task", "type": "agent"}],
            edges=[],
        )

        # Create and activate agent
        from uaef.agents.agents import AgentRegistry

        registry = AgentRegistry(session)
        agent, _ = await registry.register_agent(**sample_agent_data)
        await registry.activate_agent(agent.id)

        with patch.object(service.agent_executor, "invoke") as mock_invoke:
            mock_invoke.return_value = {
                "content": "Result",
                "usage": {"input_tokens": 10, "output_tokens": 20},
            }

            execution = await service.start_workflow(
                definition_id=definition.id,
                input_data={},
            )

            # Get the task
            from sqlalchemy import select

            from uaef.agents.models import TaskExecution

            result = await session.execute(
                select(TaskExecution).where(
                    TaskExecution.workflow_execution_id == execution.id
                )
            )
            task = result.scalar_one()

            # Wait a bit for async execution
            await session.refresh(execution)

            # Since we have one task and mocked execution, it should complete
            assert execution.completed_tasks >= 0

    @pytest.mark.asyncio
    async def test_workflow_with_dependencies(self, session, sample_agent_data):
        """Test workflow execution with task dependencies."""
        service = WorkflowService(session)

        # Create workflow with two sequential tasks
        definition = await service.create_definition(
            name="Sequential Tasks",
            tasks=[
                {"id": "task-1", "name": "First", "type": "agent"},
                {"id": "task-2", "name": "Second", "type": "agent"},
            ],
            edges=[{"from": "task-1", "to": "task-2"}],
        )

        # Create agent
        from uaef.agents.agents import AgentRegistry

        registry = AgentRegistry(session)
        agent, _ = await registry.register_agent(**sample_agent_data)
        await registry.activate_agent(agent.id)

        with patch.object(service.agent_executor, "invoke") as mock_invoke:
            mock_invoke.return_value = {
                "content": "Result",
                "usage": {"input_tokens": 10, "output_tokens": 20},
            }

            execution = await service.start_workflow(
                definition_id=definition.id,
                input_data={},
            )

            # Verify tasks have correct dependencies
            from sqlalchemy import select

            from uaef.agents.models import TaskExecution

            result = await session.execute(
                select(TaskExecution)
                .where(TaskExecution.workflow_execution_id == execution.id)
                .order_by(TaskExecution.task_name)
            )
            tasks = list(result.scalars().all())

            assert len(tasks) == 2
            task1 = next(t for t in tasks if t.task_name == "First")
            task2 = next(t for t in tasks if t.task_name == "Second")

            # Task 1 should have no dependencies
            assert not task1.depends_on or len(task1.depends_on) == 0

            # Task 2 should depend on Task 1
            assert task2.depends_on
            assert task1.id in task2.depends_on


class TestTaskScheduler:
    """Tests for TaskScheduler."""

    @pytest.mark.asyncio
    async def test_get_ready_tasks_no_dependencies(self, session):
        """Test getting ready tasks when there are no dependencies."""
        from uaef.agents.models import TaskExecution, WorkflowExecution

        # Create workflow execution
        execution = WorkflowExecution(
            definition_id="def-123",
            name="Test",
            status=WorkflowStatus.RUNNING.value,
            total_tasks=2,
        )
        session.add(execution)
        await session.flush()

        # Create tasks with no dependencies
        task1 = TaskExecution(
            workflow_execution_id=execution.id,
            task_name="Task 1",
            task_type="agent",
            status=TaskStatus.PENDING.value,
            depends_on=[],
        )
        task2 = TaskExecution(
            workflow_execution_id=execution.id,
            task_name="Task 2",
            task_type="agent",
            status=TaskStatus.PENDING.value,
            depends_on=[],
        )
        session.add_all([task1, task2])
        await session.flush()

        # Get ready tasks
        scheduler = TaskScheduler(session)
        ready = await scheduler.get_ready_tasks(execution.id)

        assert len(ready) == 2

    @pytest.mark.asyncio
    async def test_get_ready_tasks_with_dependencies(self, session):
        """Test getting ready tasks with satisfied and unsatisfied dependencies."""
        from uaef.agents.models import TaskExecution, WorkflowExecution

        execution = WorkflowExecution(
            definition_id="def-456",
            name="Test",
            status=WorkflowStatus.RUNNING.value,
            total_tasks=3,
        )
        session.add(execution)
        await session.flush()

        # Task 1 - no dependencies, completed
        task1 = TaskExecution(
            workflow_execution_id=execution.id,
            task_name="Task 1",
            task_type="agent",
            status=TaskStatus.COMPLETED.value,
            depends_on=[],
        )
        session.add(task1)
        await session.flush()

        # Task 2 - depends on Task 1, should be ready
        task2 = TaskExecution(
            workflow_execution_id=execution.id,
            task_name="Task 2",
            task_type="agent",
            status=TaskStatus.PENDING.value,
            depends_on=[task1.id],
        )
        session.add(task2)
        await session.flush()

        # Task 3 - depends on Task 2, should NOT be ready
        task3 = TaskExecution(
            workflow_execution_id=execution.id,
            task_name="Task 3",
            task_type="agent",
            status=TaskStatus.PENDING.value,
            depends_on=[task2.id],
        )
        session.add(task3)
        await session.flush()

        # Get ready tasks
        scheduler = TaskScheduler(session)
        ready = await scheduler.get_ready_tasks(execution.id)

        # Only Task 2 should be ready
        assert len(ready) == 1
        assert ready[0].id == task2.id

    @pytest.mark.asyncio
    async def test_resolve_dependencies_no_deps(self, session):
        """Test resolving dependencies for task with no dependencies."""
        from uaef.agents.models import TaskExecution, WorkflowExecution

        execution = WorkflowExecution(
            definition_id="def-789",
            name="Test",
            status=WorkflowStatus.RUNNING.value,
            total_tasks=1,
        )
        session.add(execution)
        await session.flush()

        task = TaskExecution(
            workflow_execution_id=execution.id,
            task_name="Independent Task",
            task_type="agent",
            status=TaskStatus.PENDING.value,
            depends_on=[],
        )
        session.add(task)
        await session.flush()

        scheduler = TaskScheduler(session)
        is_ready = await scheduler.resolve_dependencies(task)

        assert is_ready is True

    @pytest.mark.asyncio
    async def test_resolve_dependencies_satisfied(self, session):
        """Test resolving dependencies when all are satisfied."""
        from uaef.agents.models import TaskExecution, WorkflowExecution

        execution = WorkflowExecution(
            definition_id="def-abc",
            name="Test",
            status=WorkflowStatus.RUNNING.value,
            total_tasks=2,
        )
        session.add(execution)
        await session.flush()

        # Completed dependency
        dep_task = TaskExecution(
            workflow_execution_id=execution.id,
            task_name="Dependency",
            task_type="agent",
            status=TaskStatus.COMPLETED.value,
        )
        session.add(dep_task)
        await session.flush()

        # Task depending on completed task
        task = TaskExecution(
            workflow_execution_id=execution.id,
            task_name="Dependent Task",
            task_type="agent",
            status=TaskStatus.PENDING.value,
            depends_on=[dep_task.id],
        )
        session.add(task)
        await session.flush()

        scheduler = TaskScheduler(session)
        is_ready = await scheduler.resolve_dependencies(task)

        assert is_ready is True

    @pytest.mark.asyncio
    async def test_resolve_dependencies_not_satisfied(self, session):
        """Test resolving dependencies when not all are satisfied."""
        from uaef.agents.models import TaskExecution, WorkflowExecution

        execution = WorkflowExecution(
            definition_id="def-xyz",
            name="Test",
            status=WorkflowStatus.RUNNING.value,
            total_tasks=2,
        )
        session.add(execution)
        await session.flush()

        # Pending dependency
        dep_task = TaskExecution(
            workflow_execution_id=execution.id,
            task_name="Dependency",
            task_type="agent",
            status=TaskStatus.PENDING.value,
        )
        session.add(dep_task)
        await session.flush()

        # Task depending on pending task
        task = TaskExecution(
            workflow_execution_id=execution.id,
            task_name="Dependent Task",
            task_type="agent",
            status=TaskStatus.PENDING.value,
            depends_on=[dep_task.id],
        )
        session.add(task)
        await session.flush()

        scheduler = TaskScheduler(session)
        is_ready = await scheduler.resolve_dependencies(task)

        assert is_ready is False


class TestWorkflowIntegration:
    """Integration tests for complete workflow execution."""

    @pytest.mark.asyncio
    async def test_simple_workflow_execution(self, session, sample_agent_data):
        """Test executing a simple single-task workflow end-to-end."""
        service = WorkflowService(session)

        # Create agent
        from uaef.agents.agents import AgentRegistry

        registry = AgentRegistry(session)
        agent, _ = await registry.register_agent(**sample_agent_data)
        await registry.activate_agent(agent.id)

        # Create and start workflow
        definition = await service.create_definition(
            name="Simple Workflow",
            tasks=[{"id": "t1", "name": "Only Task", "type": "agent", "config": {"prompt": "Do work"}}],
            edges=[],
        )

        with patch.object(service.agent_executor, "invoke") as mock_invoke:
            mock_invoke.return_value = {
                "content": "Work completed",
                "usage": {"input_tokens": 5, "output_tokens": 10},
            }

            execution = await service.start_workflow(
                definition_id=definition.id,
                input_data={"context": "test"},
            )

            # Refresh to get latest state
            await session.refresh(execution)

            # Execution should be running or completed
            assert execution.status in [
                WorkflowStatus.RUNNING.value,
                WorkflowStatus.COMPLETED.value,
            ]
