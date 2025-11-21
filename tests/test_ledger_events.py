"""
Tests for UAEF Ledger Events Module

Tests for LedgerEventService and AuditTrailService.
"""

import pytest

from uaef.ledger.events import AuditTrailService, LedgerEventService
from uaef.ledger.models import EventType


class TestLedgerEventService:
    """Tests for LedgerEventService."""

    @pytest.mark.asyncio
    async def test_record_first_event(self, session):
        """Test recording the first event in an empty ledger."""
        service = LedgerEventService(session)

        event = await service.record_event(
            event_type=EventType.WORKFLOW_STARTED,
            payload={"workflow_name": "test-workflow"},
            workflow_id="wf-123",
        )

        assert event.id is not None
        assert event.sequence_number == 1
        assert event.event_type == "workflow_started"
        assert event.workflow_id == "wf-123"
        assert event.payload == {"workflow_name": "test-workflow"}
        assert event.previous_hash is None
        assert event.event_hash is not None
        assert len(event.event_hash) == 64  # SHA256

    @pytest.mark.asyncio
    async def test_record_multiple_events(self, session):
        """Test recording multiple events creates a hash chain."""
        service = LedgerEventService(session)

        event1 = await service.record_event(
            event_type=EventType.WORKFLOW_STARTED,
            payload={"step": 1},
            workflow_id="wf-123",
        )

        event2 = await service.record_event(
            event_type=EventType.TASK_STARTED,
            payload={"step": 2},
            workflow_id="wf-123",
            task_id="task-1",
        )

        event3 = await service.record_event(
            event_type=EventType.TASK_COMPLETED,
            payload={"step": 3},
            workflow_id="wf-123",
            task_id="task-1",
        )

        # Verify sequence numbers
        assert event1.sequence_number == 1
        assert event2.sequence_number == 2
        assert event3.sequence_number == 3

        # Verify hash chain
        assert event1.previous_hash is None
        assert event2.previous_hash == event1.event_hash
        assert event3.previous_hash == event2.event_hash

    @pytest.mark.asyncio
    async def test_record_event_with_actor(self, session):
        """Test recording an event with actor information."""
        service = LedgerEventService(session)

        event = await service.record_event(
            event_type=EventType.AGENT_INVOKED,
            payload={"prompt": "test"},
            agent_id="agent-123",
            actor_type="agent",
            actor_id="agent-123",
        )

        assert event.agent_id == "agent-123"
        assert event.actor_type == "agent"
        assert event.actor_id == "agent-123"

    @pytest.mark.asyncio
    async def test_get_event(self, session):
        """Test retrieving an event by ID."""
        service = LedgerEventService(session)

        created = await service.record_event(
            event_type=EventType.WORKFLOW_CREATED,
            payload={"test": "data"},
        )

        retrieved = await service.get_event(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.event_hash == created.event_hash

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, session):
        """Test retrieving a non-existent event returns None."""
        service = LedgerEventService(session)

        result = await service.get_event("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_events_by_workflow(self, session):
        """Test retrieving all events for a workflow."""
        service = LedgerEventService(session)

        # Create events for different workflows
        await service.record_event(
            event_type=EventType.WORKFLOW_STARTED,
            payload={},
            workflow_id="wf-1",
        )
        await service.record_event(
            event_type=EventType.TASK_STARTED,
            payload={},
            workflow_id="wf-1",
        )
        await service.record_event(
            event_type=EventType.WORKFLOW_STARTED,
            payload={},
            workflow_id="wf-2",
        )

        events = await service.get_events_by_workflow("wf-1")

        assert len(events) == 2
        assert all(e.workflow_id == "wf-1" for e in events)

    @pytest.mark.asyncio
    async def test_get_events_by_workflow_with_type_filter(self, session):
        """Test filtering events by type."""
        service = LedgerEventService(session)

        await service.record_event(
            event_type=EventType.WORKFLOW_STARTED,
            payload={},
            workflow_id="wf-1",
        )
        await service.record_event(
            event_type=EventType.TASK_STARTED,
            payload={},
            workflow_id="wf-1",
        )
        await service.record_event(
            event_type=EventType.TASK_COMPLETED,
            payload={},
            workflow_id="wf-1",
        )

        events = await service.get_events_by_workflow(
            "wf-1",
            event_types=[EventType.TASK_STARTED, EventType.TASK_COMPLETED],
        )

        assert len(events) == 2
        assert events[0].event_type == "task_started"
        assert events[1].event_type == "task_completed"

    @pytest.mark.asyncio
    async def test_get_event_chain(self, session):
        """Test retrieving a chain of events by sequence number."""
        service = LedgerEventService(session)

        # Create 5 events
        for i in range(5):
            await service.record_event(
                event_type=EventType.WORKFLOW_STARTED,
                payload={"index": i},
            )

        chain = await service.get_event_chain(2, 4)

        assert len(chain) == 3
        assert chain[0].sequence_number == 2
        assert chain[1].sequence_number == 3
        assert chain[2].sequence_number == 4

    @pytest.mark.asyncio
    async def test_get_latest_sequence(self, session):
        """Test getting the latest sequence number."""
        service = LedgerEventService(session)

        # Empty ledger
        seq = await service.get_latest_sequence()
        assert seq == 0

        # After adding events
        await service.record_event(
            event_type=EventType.WORKFLOW_STARTED,
            payload={},
        )
        await service.record_event(
            event_type=EventType.WORKFLOW_COMPLETED,
            payload={},
        )

        seq = await service.get_latest_sequence()
        assert seq == 2

    @pytest.mark.asyncio
    async def test_record_event_string_type(self, session):
        """Test recording an event with string event type."""
        service = LedgerEventService(session)

        event = await service.record_event(
            event_type="custom_event",
            payload={"custom": "data"},
        )

        assert event.event_type == "custom_event"


class TestAuditTrailService:
    """Tests for AuditTrailService."""

    @pytest.mark.asyncio
    async def test_create_trail(self, session):
        """Test creating an audit trail."""
        service = AuditTrailService(session)

        trail = await service.create_trail(
            workflow_id="wf-123",
            workflow_name="Test Workflow",
            metadata={"source": "test"},
        )

        assert trail.id is not None
        assert trail.workflow_id == "wf-123"
        assert trail.workflow_name == "Test Workflow"
        assert trail.metadata == {"source": "test"}
        assert trail.status == "in_progress"
        assert trail.started_at is not None
        assert trail.completed_at is None

    @pytest.mark.asyncio
    async def test_get_trail(self, session):
        """Test retrieving an audit trail."""
        service = AuditTrailService(session)

        created = await service.create_trail(
            workflow_id="wf-456",
            workflow_name="Another Workflow",
        )

        retrieved = await service.get_trail("wf-456")

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.workflow_id == "wf-456"

    @pytest.mark.asyncio
    async def test_get_trail_not_found(self, session):
        """Test retrieving a non-existent trail returns None."""
        service = AuditTrailService(session)

        result = await service.get_trail("non-existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_trail_stats(self, session):
        """Test updating audit trail statistics."""
        service = AuditTrailService(session)

        await service.create_trail(
            workflow_id="wf-789",
            workflow_name="Stats Workflow",
        )

        await service.update_trail_stats(
            workflow_id="wf-789",
            increment_events=5,
            increment_checkpoints=3,
            increment_passed=2,
            increment_failed=1,
        )

        trail = await service.get_trail("wf-789")

        assert trail.total_events == 5
        assert trail.total_checkpoints == 3
        assert trail.passed_checkpoints == 2
        assert trail.failed_checkpoints == 1

    @pytest.mark.asyncio
    async def test_update_trail_stats_cumulative(self, session):
        """Test that stats updates are cumulative."""
        service = AuditTrailService(session)

        await service.create_trail(
            workflow_id="wf-cumulative",
            workflow_name="Cumulative Workflow",
        )

        await service.update_trail_stats(
            workflow_id="wf-cumulative",
            increment_events=3,
        )
        await service.update_trail_stats(
            workflow_id="wf-cumulative",
            increment_events=2,
        )

        trail = await service.get_trail("wf-cumulative")
        assert trail.total_events == 5

    @pytest.mark.asyncio
    async def test_complete_trail(self, session):
        """Test marking an audit trail as completed."""
        service = AuditTrailService(session)

        await service.create_trail(
            workflow_id="wf-complete",
            workflow_name="Complete Workflow",
        )

        await service.complete_trail(
            workflow_id="wf-complete",
            status="completed",
            final_hash="abc123def456",
        )

        trail = await service.get_trail("wf-complete")

        assert trail.status == "completed"
        assert trail.completed_at is not None
        assert trail.final_hash == "abc123def456"

    @pytest.mark.asyncio
    async def test_complete_trail_failed(self, session):
        """Test marking an audit trail as failed."""
        service = AuditTrailService(session)

        await service.create_trail(
            workflow_id="wf-failed",
            workflow_name="Failed Workflow",
        )

        await service.complete_trail(
            workflow_id="wf-failed",
            status="failed",
        )

        trail = await service.get_trail("wf-failed")

        assert trail.status == "failed"
        assert trail.completed_at is not None
