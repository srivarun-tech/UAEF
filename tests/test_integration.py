"""
UAEF Integration Tests

End-to-end tests validating the complete system integration.
"""

import asyncio

import pytest

from uaef.core import get_session
from uaef.core.security import HashService
from uaef.ledger import EventType, LedgerEventService, VerificationService
from uaef.agents import AgentRegistry, ClaudeAgentExecutor
from uaef.agents.models import WorkflowDefinition
from uaef.agents.workflow import TaskScheduler, WorkflowService
from uaef.settlement import SettlementService
from uaef.settlement.models import RecipientType, SettlementStatus


@pytest.mark.asyncio
class TestEndToEndWorkflow:
    """Test complete workflow execution with all components."""

    async def test_multi_task_workflow_with_dependencies(self, session):
        """Test workflow with multiple tasks and dependencies."""
        # Setup services
        agent_registry = AgentRegistry(session)
        workflow_service = WorkflowService(session)

        # Register agent
        agent, _ = await agent_registry.register_agent(
            name="Integration Test Agent",
            agent_type="claude",
            capabilities=["test"],
        )
        await agent_registry.activate_agent(agent.id)

        # Create workflow with dependencies
        workflow_def = WorkflowDefinition(
            name="Multi-Task Workflow",
            description="Test workflow with task dependencies",
            tasks=[
                {
                    "name": "task_a",
                    "task_type": "agent",
                    "agent_type": "claude",
                    "config": {"test": True},
                    "dependencies": [],
                },
                {
                    "name": "task_b",
                    "task_type": "agent",
                    "agent_type": "claude",
                    "config": {"test": True},
                    "dependencies": ["task_a"],  # Depends on task_a
                },
                {
                    "name": "task_c",
                    "task_type": "agent",
                    "agent_type": "claude",
                    "config": {"test": True},
                    "dependencies": ["task_a"],  # Also depends on task_a
                },
                {
                    "name": "task_d",
                    "task_type": "agent",
                    "agent_type": "claude",
                    "config": {"test": True},
                    "dependencies": ["task_b", "task_c"],  # Depends on both b and c
                },
            ],
        )
        session.add(workflow_def)
        await session.commit()
        await session.refresh(workflow_def)

        # Start workflow
        execution = await workflow_service.start_workflow(
            definition_id=workflow_def.id,
            input_data={"test": "data"},
            initiated_by="integration_test",
        )

        assert execution is not None
        assert execution.status == "running"
        assert execution.total_tasks == 4
        assert execution.completed_tasks == 0

        # Get task scheduler
        scheduler = TaskScheduler(session)

        # Verify task execution order
        # Initially only task_a should be ready (no dependencies)
        ready_tasks = await scheduler.get_ready_tasks(execution.id)
        assert len(ready_tasks) == 1
        assert ready_tasks[0].task_name == "task_a"

        # Complete task_a
        await workflow_service.complete_task(
            task_id=ready_tasks[0].id,
            output_data={"result": "task_a_complete"},
        )

        # Now task_b and task_c should be ready
        ready_tasks = await scheduler.get_ready_tasks(execution.id)
        assert len(ready_tasks) == 2
        task_names = {t.task_name for t in ready_tasks}
        assert task_names == {"task_b", "task_c"}

        # Complete task_b and task_c
        for task in ready_tasks:
            await workflow_service.complete_task(
                task_id=task.id,
                output_data={"result": f"{task.task_name}_complete"},
            )

        # Now task_d should be ready
        ready_tasks = await scheduler.get_ready_tasks(execution.id)
        assert len(ready_tasks) == 1
        assert ready_tasks[0].task_name == "task_d"

        # Complete task_d
        await workflow_service.complete_task(
            task_id=ready_tasks[0].id,
            output_data={"result": "task_d_complete"},
        )

        # Verify workflow completed
        await session.refresh(execution)
        assert execution.status == "completed"
        assert execution.completed_tasks == 4


    async def test_ledger_integrity_verification(self, session):
        """Test ledger hash chain integrity."""
        ledger_service = LedgerEventService(session)
        verification_service = VerificationService(session)
        hash_service = HashService()

        # Record a series of events
        workflow_id = "test-workflow-123"
        events = []

        for i in range(10):
            event = await ledger_service.record_event(
                event_type=EventType.TASK_STARTED,
                payload={"task_number": i},
                workflow_id=workflow_id,
            )
            events.append(event)

        # Verify each event's hash chain
        for i, event in enumerate(events):
            if i == 0:
                # First event should have genesis hash as previous
                assert event.previous_hash is not None
            else:
                # Subsequent events should chain to previous
                assert event.previous_hash == events[i-1].event_hash

            # Verify event hash
            computed_hash = hash_service.hash_event(
                sequence=event.sequence_number,
                event_type=event.event_type,
                payload=event.payload,
                previous_hash=event.previous_hash,
            )
            assert event.event_hash == computed_hash

        # Verify entire chain
        is_valid, errors = await verification_service.verify_chain_range(
            start_sequence=events[0].sequence_number,
            end_sequence=events[-1].sequence_number,
        )
        assert is_valid
        assert len(errors) == 0


    async def test_settlement_signal_generation(self, session):
        """Test settlement signal generation on workflow completion."""
        # Setup services
        agent_registry = AgentRegistry(session)
        workflow_service = WorkflowService(session)
        settlement_service = SettlementService(session)

        # Register agent
        agent, _ = await agent_registry.register_agent(
            name="Settlement Test Agent",
            agent_type="claude",
            capabilities=["test"],
        )
        await agent_registry.activate_agent(agent.id)

        # Create workflow
        workflow_def = WorkflowDefinition(
            name="Settlement Test Workflow",
            description="Test settlement generation",
            tasks=[
                {
                    "name": "single_task",
                    "task_type": "agent",
                    "agent_type": "claude",
                    "config": {"test": True},
                    "dependencies": [],
                },
            ],
        )
        session.add(workflow_def)
        await session.commit()
        await session.refresh(workflow_def)

        # Create settlement rule
        rule = await settlement_service.create_rule(
            name="test_settlement_rule",
            workflow_definition_id=workflow_def.id,
            trigger_conditions={"status": {"$eq": "completed"}},
            amount_type="fixed",
            fixed_amount=100.00,
            currency="USD",
            recipient_type=RecipientType.AGENT,
            fixed_recipient_id=agent.id,
        )

        # Start workflow
        execution = await workflow_service.start_workflow(
            definition_id=workflow_def.id,
            input_data={"test": "data"},
            initiated_by="settlement_test",
        )

        # Get and complete the task
        scheduler = TaskScheduler(session)
        ready_tasks = await scheduler.get_ready_tasks(execution.id)
        assert len(ready_tasks) == 1

        await workflow_service.complete_task(
            task_id=ready_tasks[0].id,
            output_data={"result": "complete"},
        )

        # Verify workflow completed
        await session.refresh(execution)
        assert execution.status == "completed"

        # Check for settlement signal
        from sqlalchemy import select
        from uaef.settlement.models import SettlementSignal

        result = await session.execute(
            select(SettlementSignal).where(
                SettlementSignal.workflow_execution_id == execution.id
            )
        )
        signals = result.scalars().all()

        assert len(signals) == 1
        signal = signals[0]
        assert signal.amount == 100.00
        assert signal.currency == "USD"
        assert signal.status == SettlementStatus.PENDING.value
        assert signal.recipient_id == agent.id
        assert signal.settlement_rule_id == rule.id


    async def test_complete_workflow_with_ledger_and_settlement(self, session):
        """Integration test: Complete workflow with ledger tracking and settlement."""
        # Setup all services
        agent_registry = AgentRegistry(session)
        workflow_service = WorkflowService(session)
        settlement_service = SettlementService(session)
        ledger_service = LedgerEventService(session)

        # Get initial ledger sequence
        initial_sequence = await ledger_service.get_latest_sequence()

        # Register agent
        agent, _ = await agent_registry.register_agent(
            name="Complete Test Agent",
            agent_type="claude",
            capabilities=["processing"],
        )
        await agent_registry.activate_agent(agent.id)

        # Create workflow with 2 tasks
        workflow_def = WorkflowDefinition(
            name="Complete Integration Workflow",
            description="Full integration test",
            tasks=[
                {
                    "name": "process",
                    "task_type": "agent",
                    "agent_type": "claude",
                    "config": {},
                    "dependencies": [],
                },
                {
                    "name": "finalize",
                    "task_type": "agent",
                    "agent_type": "claude",
                    "config": {},
                    "dependencies": ["process"],
                },
            ],
        )
        session.add(workflow_def)
        await session.commit()
        await session.refresh(workflow_def)

        # Create settlement rule
        rule = await settlement_service.create_rule(
            name="complete_test_fee",
            workflow_definition_id=workflow_def.id,
            trigger_conditions={"status": {"$eq": "completed"}},
            amount_type="fixed",
            fixed_amount=50.00,
            currency="USD",
            recipient_type=RecipientType.AGENT,
            fixed_recipient_id=agent.id,
        )

        # Start workflow
        execution = await workflow_service.start_workflow(
            definition_id=workflow_def.id,
            input_data={"document": "test.pdf"},
            initiated_by="integration_test",
        )

        # Execute tasks
        scheduler = TaskScheduler(session)

        # Task 1
        tasks = await scheduler.get_ready_tasks(execution.id)
        assert len(tasks) == 1
        await workflow_service.complete_task(
            task_id=tasks[0].id,
            output_data={"processed": True},
        )

        # Task 2
        tasks = await scheduler.get_ready_tasks(execution.id)
        assert len(tasks) == 1
        await workflow_service.complete_task(
            task_id=tasks[0].id,
            output_data={"finalized": True},
        )

        # Verify workflow completed
        await session.refresh(execution)
        assert execution.status == "completed"
        assert execution.completed_tasks == 2

        # Verify ledger events were recorded
        final_sequence = await ledger_service.get_latest_sequence()
        assert final_sequence > initial_sequence

        events = await ledger_service.get_events_by_workflow(execution.id)
        event_types = [e.event_type for e in events]

        # Should have: workflow_started, task_started (x2), task_completed (x2),
        # workflow_completed, settlement_triggered
        assert EventType.WORKFLOW_STARTED.value in event_types
        assert EventType.WORKFLOW_COMPLETED.value in event_types
        assert EventType.SETTLEMENT_TRIGGERED.value in event_types

        # Verify settlement signal
        from sqlalchemy import select
        from uaef.settlement.models import SettlementSignal

        result = await session.execute(
            select(SettlementSignal).where(
                SettlementSignal.workflow_execution_id == execution.id
            )
        )
        signals = result.scalars().all()

        assert len(signals) == 1
        assert signals[0].amount == 50.00
        assert signals[0].recipient_id == agent.id

        # Verify agent metrics updated
        await session.refresh(agent)
        assert agent.total_tasks >= 2
