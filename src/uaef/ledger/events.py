"""
UAEF Ledger Event Service

Service for recording immutable events to the trust ledger
with cryptographic chain verification.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from uaef.core.logging import get_logger
from uaef.core.security import HashService, generate_event_id
from uaef.ledger.models import AuditTrail, EventType, LedgerEvent

logger = get_logger(__name__)


class LedgerEventService:
    """Service for recording and querying ledger events."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.hash_service = HashService()

    async def record_event(
        self,
        event_type: EventType | str,
        payload: dict[str, Any],
        workflow_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        actor_type: str = "system",
        actor_id: str | None = None,
    ) -> LedgerEvent:
        """
        Record a new event to the trust ledger.

        Creates a cryptographic hash chain linking to the previous event.
        """
        # Get the next sequence number and previous hash
        result = await self.session.execute(
            select(
                func.coalesce(func.max(LedgerEvent.sequence_number), 0),
            )
        )
        last_sequence = result.scalar() or 0
        next_sequence = last_sequence + 1

        # Get previous event hash
        previous_hash = None
        if last_sequence > 0:
            result = await self.session.execute(
                select(LedgerEvent.event_hash)
                .where(LedgerEvent.sequence_number == last_sequence)
            )
            previous_hash = result.scalar()

        # Prepare event data for hashing
        event_type_str = event_type.value if isinstance(event_type, EventType) else event_type
        hash_data = {
            "sequence": next_sequence,
            "type": event_type_str,
            "workflow_id": workflow_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "payload": payload,
            "previous_hash": previous_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Calculate event hash
        if previous_hash:
            event_hash = self.hash_service.hash_chain(
                previous_hash,
                self.hash_service.hash_event(hash_data),
            )
        else:
            event_hash = self.hash_service.hash_event(hash_data)

        # Create event record
        event = LedgerEvent(
            id=generate_event_id(),
            sequence_number=next_sequence,
            event_type=event_type_str,
            workflow_id=workflow_id,
            task_id=task_id,
            agent_id=agent_id,
            payload=payload,
            actor_type=actor_type,
            actor_id=actor_id,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )

        self.session.add(event)
        await self.session.flush()

        logger.info(
            "ledger_event_recorded",
            event_id=event.id,
            event_type=event_type_str,
            sequence=next_sequence,
            workflow_id=workflow_id,
        )

        return event

    async def get_event(self, event_id: str) -> LedgerEvent | None:
        """Get a single event by ID."""
        result = await self.session.execute(
            select(LedgerEvent).where(LedgerEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_events_by_workflow(
        self,
        workflow_id: str,
        event_types: list[EventType | str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LedgerEvent]:
        """Get events for a specific workflow."""
        query = (
            select(LedgerEvent)
            .where(LedgerEvent.workflow_id == workflow_id)
            .order_by(LedgerEvent.sequence_number)
            .limit(limit)
            .offset(offset)
        )

        if event_types:
            type_values = [
                t.value if isinstance(t, EventType) else t for t in event_types
            ]
            query = query.where(LedgerEvent.event_type.in_(type_values))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_event_chain(
        self,
        start_sequence: int,
        end_sequence: int,
    ) -> list[LedgerEvent]:
        """Get a chain of events by sequence number range."""
        result = await self.session.execute(
            select(LedgerEvent)
            .where(
                LedgerEvent.sequence_number >= start_sequence,
                LedgerEvent.sequence_number <= end_sequence,
            )
            .order_by(LedgerEvent.sequence_number)
        )
        return list(result.scalars().all())

    async def verify_chain(
        self,
        start_sequence: int,
        end_sequence: int,
    ) -> tuple[bool, str | None]:
        """
        Verify the hash chain integrity for a range of events.

        Returns:
            Tuple of (is_valid, error_message)
        """
        events = await self.get_event_chain(start_sequence, end_sequence)

        if not events:
            return True, None

        for i, event in enumerate(events):
            # Reconstruct expected hash
            hash_data = {
                "sequence": event.sequence_number,
                "type": event.event_type,
                "workflow_id": event.workflow_id,
                "task_id": event.task_id,
                "agent_id": event.agent_id,
                "actor_type": event.actor_type,
                "actor_id": event.actor_id,
                "payload": event.payload,
                "previous_hash": event.previous_hash,
                "timestamp": event.created_at.isoformat(),
            }

            if event.previous_hash:
                expected_hash = self.hash_service.hash_chain(
                    event.previous_hash,
                    self.hash_service.hash_event(hash_data),
                )
            else:
                expected_hash = self.hash_service.hash_event(hash_data)

            # Verify hash
            if event.event_hash != expected_hash:
                return False, f"Hash mismatch at sequence {event.sequence_number}"

            # Verify chain linkage (except for first event)
            if i > 0:
                previous_event = events[i - 1]
                if event.previous_hash != previous_event.event_hash:
                    return (
                        False,
                        f"Chain break at sequence {event.sequence_number}",
                    )

        return True, None

    async def get_latest_sequence(self) -> int:
        """Get the latest sequence number in the ledger."""
        result = await self.session.execute(
            select(func.coalesce(func.max(LedgerEvent.sequence_number), 0))
        )
        return result.scalar() or 0


class AuditTrailService:
    """Service for managing audit trails."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_trail(
        self,
        workflow_id: str,
        workflow_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditTrail:
        """Create a new audit trail for a workflow."""
        trail = AuditTrail(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            started_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        self.session.add(trail)
        await self.session.flush()
        return trail

    async def get_trail(self, workflow_id: str) -> AuditTrail | None:
        """Get audit trail by workflow ID."""
        result = await self.session.execute(
            select(AuditTrail).where(AuditTrail.workflow_id == workflow_id)
        )
        return result.scalar_one_or_none()

    async def update_trail_stats(
        self,
        workflow_id: str,
        increment_events: int = 0,
        increment_checkpoints: int = 0,
        increment_passed: int = 0,
        increment_failed: int = 0,
    ) -> None:
        """Update audit trail statistics."""
        trail = await self.get_trail(workflow_id)
        if trail:
            trail.total_events += increment_events
            trail.total_checkpoints += increment_checkpoints
            trail.passed_checkpoints += increment_passed
            trail.failed_checkpoints += increment_failed
            await self.session.flush()

    async def complete_trail(
        self,
        workflow_id: str,
        status: str,
        final_hash: str | None = None,
    ) -> None:
        """Mark an audit trail as completed."""
        trail = await self.get_trail(workflow_id)
        if trail:
            trail.status = status
            trail.completed_at = datetime.now(timezone.utc)
            trail.final_hash = final_hash
            await self.session.flush()
