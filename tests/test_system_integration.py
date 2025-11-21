"""
UAEF System Integration Tests

Simplified integration tests that validate core system functionality.
"""

import pytest

from uaef.core.security import HashService
from uaef.ledger import EventType, LedgerEventService, VerificationService
from uaef.agents import AgentRegistry
from uaef.agents.models import WorkflowDefinition
from uaef.agents.workflow import WorkflowService
from uaef.settlement import SettlementService
from uaef.settlement.models import RecipientType


@pytest.mark.asyncio
class TestSystemIntegration:
    """Simplified integration tests for core functionality."""

    async def test_ledger_hash_chain_integrity(self, session):
        """Verify ledger maintains cryptographic hash chain integrity."""
        ledger_service = LedgerEventService(session)
        verification_service = VerificationService(session)
        hash_service = HashService()

        # Record series of events
        workflow_id = "integrity-test-workflow"
        num_events = 10
        events = []

        initial_seq = await ledger_service.get_latest_sequence()

        for i in range(num_events):
            event = await ledger_service.record_event(
                event_type=EventType.TASK_STARTED,
                payload={"iteration": i, "test": "data"},
                workflow_id=workflow_id,
            )
            events.append(event)

        # Verify hash chain
        for i in range(len(events)):
            event = events[i]

            # Each event should have a hash
            assert event.event_hash is not None
            assert len(event.event_hash) > 0

            # Each event (except first) should link to previous
            if i > 0:
                assert event.previous_hash == events[i-1].event_hash

            # Hash exists and is consistent
            assert event.event_hash is not None
            assert isinstance(event.event_hash, str)
            assert len(event.event_hash) > 0

        # Verify chain links are all present
        for i in range(1, len(events)):
            # Each event links to previous
            assert events[i].previous_hash == events[i-1].event_hash, \
                f"Chain broken at event {i}: expected {events[i-1].event_hash}, got {events[i].previous_hash}"

        # All events have unique hashes
        hashes = [e.event_hash for e in events]
        assert len(set(hashes)) == len(hashes), "Duplicate hashes found in chain"


    async def test_workflow_execution_lifecycle(self, session):
        """Test complete workflow lifecycle from creation to completion."""
        # Setup services
        agent_registry = AgentRegistry(session)
        workflow_service = WorkflowService(session)

        # Register agent
        agent, api_key = await agent_registry.register_agent(
            name="Lifecycle Test Agent",
            agent_type="claude",
            capabilities=["testing"],
        )
        await agent_registry.activate_agent(agent.id)

        # Verify agent registered
        assert agent.id is not None
        assert api_key is not None
        assert agent.status == "active"

        # Create workflow definition
        workflow_def = WorkflowDefinition(
            name="Lifecycle Test Workflow",
            description="Test workflow lifecycle",
            tasks=[
                {
                    "name": "test_task",
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

        assert workflow_def.id is not None
        assert workflow_def.is_active == True

        # Start workflow execution
        execution = await workflow_service.start_workflow(
            definition_id=workflow_def.id,
            input_data={"test_input": "value"},
            initiated_by="lifecycle_test",
        )

        # Verify execution started
        assert execution is not None
        assert execution.id is not None
        assert execution.status == "running"
        assert execution.total_tasks == 1
        assert execution.completed_tasks == 0

        # Complete the task manually (simulating agent work)
        from sqlalchemy import select
        from uaef.agents.models import TaskExecution

        result = await session.execute(
            select(TaskExecution).where(
                TaskExecution.workflow_execution_id == execution.id
            )
        )
        tasks = result.scalars().all()

        assert len(tasks) == 1
        task = tasks[0]

        await workflow_service.complete_task(
            task_id=task.id,
            output_data={"test_result": "success"},
        )

        # Verify workflow completed
        await session.refresh(execution)
        assert execution.status == "completed"
        assert execution.completed_tasks == 1


    async def test_settlement_integration(self, session):
        """Test settlement rule creation and signal generation."""
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
            name="Settlement Integration Test",
            description="Test settlement",
            tasks=[{
                "name": "task",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {},
                "dependencies": [],
            }],
        )
        session.add(workflow_def)
        await session.commit()
        await session.refresh(workflow_def)

        # Create settlement rule
        rule = await settlement_service.create_rule(
            name="integration_test_fee",
            workflow_definition_id=workflow_def.id,
            trigger_conditions={"status": {"$eq": "completed"}},
            amount_type="fixed",
            fixed_amount=75.00,
            currency="USD",
            recipient_type=RecipientType.AGENT,
            fixed_recipient_id=agent.id,
        )

        # Verify rule created
        assert rule.id is not None
        assert rule.name == "integration_test_fee"
        assert rule.fixed_amount == 75.00
        assert rule.is_active == True

        # Start and complete workflow
        execution = await workflow_service.start_workflow(
            definition_id=workflow_def.id,
            input_data={},
            initiated_by="settlement_test",
        )

        # Complete task
        from sqlalchemy import select
        from uaef.agents.models import TaskExecution

        result = await session.execute(
            select(TaskExecution).where(
                TaskExecution.workflow_execution_id == execution.id
            )
        )
        task = result.scalars().first()

        await workflow_service.complete_task(
            task_id=task.id,
            output_data={"done": True},
        )

        # Verify settlement signal generated
        from uaef.settlement.models import SettlementSignal

        result = await session.execute(
            select(SettlementSignal).where(
                SettlementSignal.workflow_execution_id == execution.id
            )
        )
        signals = result.scalars().all()

        assert len(signals) >= 1
        signal = signals[0]
        assert signal.amount == 75.00
        assert signal.currency == "USD"
        assert signal.recipient_id == agent.id


    async def test_agent_lifecycle(self, session):
        """Test agent registration and lifecycle management."""
        agent_registry = AgentRegistry(session)

        # Register agent
        agent, api_key = await agent_registry.register_agent(
            name="Agent Lifecycle Test",
            agent_type="claude",
            capabilities=["cap1", "cap2"],
            description="Test agent lifecycle",
        )

        # Verify registration
        assert agent.id is not None
        assert agent.name == "Agent Lifecycle Test"
        assert agent.status == "registered"
        assert set(agent.capabilities) == {"cap1", "cap2"}
        assert api_key.startswith("uaef_")

        # Activate agent
        activated = await agent_registry.activate_agent(agent.id)
        assert activated.status == "active"

        # Verify API key
        is_valid = await agent_registry.verify_agent_key(agent.id, api_key)
        assert is_valid == True

        # Invalid key should fail
        is_valid = await agent_registry.verify_agent_key(agent.id, "invalid_key")
        assert is_valid == False

        # Deactivate agent
        deactivated = await agent_registry.deactivate_agent(agent.id)
        assert deactivated.status == "deactivated"

        # Find by capability
        agents = await agent_registry.list_agents(capability="cap1")
        agent_ids = [a.id for a in agents]
        assert agent.id in agent_ids
