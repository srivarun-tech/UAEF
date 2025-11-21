"""
UAEF Ledger Verification Service

Provides verification and integrity checking for the trust ledger,
including hash chain validation and block finalization.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from uaef.core.logging import get_logger
from uaef.core.security import HashService
from uaef.ledger.models import LedgerBlock, LedgerEvent

logger = get_logger(__name__)


class VerificationService:
    """Service for ledger integrity verification."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.hash_service = HashService()

    async def verify_event(self, event_id: str) -> tuple[bool, str | None]:
        """
        Verify a single event's hash integrity.

        Returns:
            Tuple of (is_valid, error_message)
        """
        result = await self.session.execute(
            select(LedgerEvent).where(LedgerEvent.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            return False, f"Event {event_id} not found"

        # Reconstruct hash
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

        if event.event_hash != expected_hash:
            return False, f"Hash mismatch for event {event_id}"

        return True, None

    async def verify_chain_range(
        self,
        start_sequence: int,
        end_sequence: int,
    ) -> tuple[bool, list[dict[str, Any]]]:
        """
        Verify a range of events in the chain.

        Returns:
            Tuple of (all_valid, list_of_errors)
        """
        result = await self.session.execute(
            select(LedgerEvent)
            .where(
                LedgerEvent.sequence_number >= start_sequence,
                LedgerEvent.sequence_number <= end_sequence,
            )
            .order_by(LedgerEvent.sequence_number)
        )
        events = list(result.scalars().all())

        errors: list[dict[str, Any]] = []
        previous_hash: str | None = None

        for event in events:
            # Check chain continuity
            if event.previous_hash != previous_hash:
                errors.append({
                    "sequence": event.sequence_number,
                    "error": "Chain break - previous hash mismatch",
                    "expected": previous_hash,
                    "actual": event.previous_hash,
                })

            # Verify individual event
            is_valid, error = await self.verify_event(event.id)
            if not is_valid:
                errors.append({
                    "sequence": event.sequence_number,
                    "error": error,
                })

            previous_hash = event.event_hash

        return len(errors) == 0, errors

    async def create_block(
        self,
        start_sequence: int,
        end_sequence: int,
    ) -> LedgerBlock:
        """
        Create a verification block for a range of events.

        Blocks provide efficient batch verification with Merkle roots.
        """
        # Get events in range
        result = await self.session.execute(
            select(LedgerEvent)
            .where(
                LedgerEvent.sequence_number >= start_sequence,
                LedgerEvent.sequence_number <= end_sequence,
            )
            .order_by(LedgerEvent.sequence_number)
        )
        events = list(result.scalars().all())

        if not events:
            raise ValueError(f"No events found in range {start_sequence}-{end_sequence}")

        # Calculate Merkle root
        merkle_root = self._calculate_merkle_root(
            [e.event_hash for e in events]
        )

        # Get previous block hash
        result = await self.session.execute(
            select(LedgerBlock)
            .order_by(LedgerBlock.block_number.desc())
            .limit(1)
        )
        previous_block = result.scalar_one_or_none()
        previous_block_hash = previous_block.block_hash if previous_block else None

        # Get next block number
        result = await self.session.execute(
            select(func.coalesce(func.max(LedgerBlock.block_number), 0))
        )
        next_block_number = (result.scalar() or 0) + 1

        # Calculate block hash
        block_data = {
            "block_number": next_block_number,
            "start_sequence": start_sequence,
            "end_sequence": end_sequence,
            "merkle_root": merkle_root,
            "previous_block_hash": previous_block_hash,
        }
        block_hash = self.hash_service.hash_event(block_data)

        # Create block
        block = LedgerBlock(
            block_number=next_block_number,
            start_sequence=start_sequence,
            end_sequence=end_sequence,
            event_count=len(events),
            previous_block_hash=previous_block_hash,
            block_hash=block_hash,
            merkle_root=merkle_root,
        )

        self.session.add(block)
        await self.session.flush()

        logger.info(
            "block_created",
            block_number=next_block_number,
            event_count=len(events),
            merkle_root=merkle_root,
        )

        return block

    def _calculate_merkle_root(self, hashes: list[str]) -> str:
        """Calculate Merkle root from a list of hashes."""
        if not hashes:
            return self.hash_service.hash("")

        if len(hashes) == 1:
            return hashes[0]

        # Build Merkle tree
        current_level = hashes.copy()

        while len(current_level) > 1:
            next_level: list[str] = []

            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = self.hash_service.hash(left + right)
                next_level.append(combined)

            current_level = next_level

        return current_level[0]

    async def verify_block(self, block_number: int) -> tuple[bool, str | None]:
        """
        Verify a block's integrity.

        Returns:
            Tuple of (is_valid, error_message)
        """
        result = await self.session.execute(
            select(LedgerBlock).where(LedgerBlock.block_number == block_number)
        )
        block = result.scalar_one_or_none()

        if not block:
            return False, f"Block {block_number} not found"

        # Get events in block
        result = await self.session.execute(
            select(LedgerEvent)
            .where(
                LedgerEvent.sequence_number >= block.start_sequence,
                LedgerEvent.sequence_number <= block.end_sequence,
            )
            .order_by(LedgerEvent.sequence_number)
        )
        events = list(result.scalars().all())

        # Verify Merkle root
        expected_root = self._calculate_merkle_root(
            [e.event_hash for e in events]
        )
        if block.merkle_root != expected_root:
            return False, f"Merkle root mismatch for block {block_number}"

        # Verify block hash
        block_data = {
            "block_number": block.block_number,
            "start_sequence": block.start_sequence,
            "end_sequence": block.end_sequence,
            "merkle_root": block.merkle_root,
            "previous_block_hash": block.previous_block_hash,
        }
        expected_hash = self.hash_service.hash_event(block_data)
        if block.block_hash != expected_hash:
            return False, f"Block hash mismatch for block {block_number}"

        return True, None

    async def get_verification_summary(self) -> dict[str, Any]:
        """Get a summary of ledger verification status."""
        # Get event counts
        result = await self.session.execute(
            select(func.count(LedgerEvent.id))
        )
        total_events = result.scalar() or 0

        # Get block counts
        result = await self.session.execute(
            select(func.count(LedgerBlock.id))
        )
        total_blocks = result.scalar() or 0

        # Get latest sequence
        result = await self.session.execute(
            select(func.max(LedgerEvent.sequence_number))
        )
        latest_sequence = result.scalar() or 0

        # Get latest block
        result = await self.session.execute(
            select(LedgerBlock)
            .order_by(LedgerBlock.block_number.desc())
            .limit(1)
        )
        latest_block = result.scalar_one_or_none()

        return {
            "total_events": total_events,
            "total_blocks": total_blocks,
            "latest_sequence": latest_sequence,
            "latest_block_number": latest_block.block_number if latest_block else 0,
            "unblocked_events": (
                latest_sequence - latest_block.end_sequence
                if latest_block
                else latest_sequence
            ),
        }
