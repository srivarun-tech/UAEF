"""
UAEF Compliance Checkpoint Service

Manages compliance checkpoints and rule enforcement
for workflow verification.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uaef.core.logging import get_logger
from uaef.ledger.models import (
    CheckpointStatus,
    ComplianceCheckpoint,
    EventType,
)

logger = get_logger(__name__)


class ComplianceRule:
    """Base class for compliance rules."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    async def evaluate(
        self,
        context: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        """
        Evaluate the rule against the given context.

        Returns:
            Tuple of (passed, result_details)
        """
        raise NotImplementedError


class RequiredFieldRule(ComplianceRule):
    """Rule that checks for required fields in the context."""

    def __init__(self, name: str, required_fields: list[str], description: str = ""):
        super().__init__(name, description)
        self.required_fields = required_fields

    async def evaluate(
        self,
        context: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        missing = [f for f in self.required_fields if f not in context]
        passed = len(missing) == 0
        return passed, {
            "required": self.required_fields,
            "missing": missing,
        }


class ThresholdRule(ComplianceRule):
    """Rule that checks if a value meets a threshold."""

    def __init__(
        self,
        name: str,
        field: str,
        min_value: float | None = None,
        max_value: float | None = None,
        description: str = "",
    ):
        super().__init__(name, description)
        self.field = field
        self.min_value = min_value
        self.max_value = max_value

    async def evaluate(
        self,
        context: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        value = context.get(self.field)
        if value is None:
            return False, {"error": f"Field {self.field} not found"}

        passed = True
        if self.min_value is not None and value < self.min_value:
            passed = False
        if self.max_value is not None and value > self.max_value:
            passed = False

        return passed, {
            "field": self.field,
            "value": value,
            "min": self.min_value,
            "max": self.max_value,
        }


class ComplianceService:
    """Service for managing compliance checkpoints."""

    def __init__(self, session: AsyncSession):
        # Lazy import to avoid circular dependency
        from uaef.ledger.events import LedgerEventService

        self.session = session
        self.event_service = LedgerEventService(session)

    async def create_checkpoint(
        self,
        name: str,
        workflow_id: str,
        rule_definition: dict[str, Any],
        task_id: str | None = None,
        description: str | None = None,
    ) -> ComplianceCheckpoint:
        """Create a new compliance checkpoint."""
        checkpoint = ComplianceCheckpoint(
            name=name,
            description=description,
            workflow_id=workflow_id,
            task_id=task_id,
            rule_definition=rule_definition,
        )
        self.session.add(checkpoint)
        await self.session.flush()

        logger.info(
            "checkpoint_created",
            checkpoint_id=checkpoint.id,
            name=name,
            workflow_id=workflow_id,
        )

        return checkpoint

    async def evaluate_checkpoint(
        self,
        checkpoint_id: str,
        context: dict[str, Any],
    ) -> ComplianceCheckpoint:
        """
        Evaluate a checkpoint against the provided context.

        Records the result in the ledger.
        """
        result = await self.session.execute(
            select(ComplianceCheckpoint).where(
                ComplianceCheckpoint.id == checkpoint_id
            )
        )
        checkpoint = result.scalar_one_or_none()

        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        # Evaluate based on rule type
        rule_type = checkpoint.rule_definition.get("type", "required_fields")
        passed = False
        result_data: dict[str, Any] = {}

        if rule_type == "required_fields":
            rule = RequiredFieldRule(
                checkpoint.name,
                checkpoint.rule_definition.get("fields", []),
            )
            passed, result_data = await rule.evaluate(context)

        elif rule_type == "threshold":
            rule = ThresholdRule(
                checkpoint.name,
                checkpoint.rule_definition.get("field", ""),
                checkpoint.rule_definition.get("min"),
                checkpoint.rule_definition.get("max"),
            )
            passed, result_data = await rule.evaluate(context)

        # Update checkpoint
        checkpoint.status = (
            CheckpointStatus.PASSED if passed else CheckpointStatus.FAILED
        )
        checkpoint.verification_result = result_data
        checkpoint.verified_at = datetime.now(timezone.utc)

        # Record in ledger
        event_type = (
            EventType.CHECKPOINT_PASSED if passed else EventType.CHECKPOINT_FAILED
        )
        event = await self.event_service.record_event(
            event_type=event_type,
            payload={
                "checkpoint_id": checkpoint.id,
                "checkpoint_name": checkpoint.name,
                "result": result_data,
            },
            workflow_id=checkpoint.workflow_id,
            task_id=checkpoint.task_id,
        )

        checkpoint.ledger_event_id = event.id
        await self.session.flush()

        logger.info(
            "checkpoint_evaluated",
            checkpoint_id=checkpoint.id,
            status=checkpoint.status,
            workflow_id=checkpoint.workflow_id,
        )

        return checkpoint

    async def get_checkpoint(self, checkpoint_id: str) -> ComplianceCheckpoint | None:
        """Get a checkpoint by ID."""
        result = await self.session.execute(
            select(ComplianceCheckpoint).where(
                ComplianceCheckpoint.id == checkpoint_id
            )
        )
        return result.scalar_one_or_none()

    async def get_checkpoints_by_workflow(
        self,
        workflow_id: str,
        status: CheckpointStatus | None = None,
    ) -> list[ComplianceCheckpoint]:
        """Get all checkpoints for a workflow."""
        query = select(ComplianceCheckpoint).where(
            ComplianceCheckpoint.workflow_id == workflow_id
        )

        if status:
            query = query.where(ComplianceCheckpoint.status == status)

        result = await self.session.execute(
            query.order_by(ComplianceCheckpoint.created_at)
        )
        return list(result.scalars().all())

    async def get_pending_checkpoints(
        self,
        workflow_id: str,
    ) -> list[ComplianceCheckpoint]:
        """Get pending checkpoints for a workflow."""
        return await self.get_checkpoints_by_workflow(
            workflow_id,
            status=CheckpointStatus.PENDING,
        )

    async def require_human_review(
        self,
        checkpoint_id: str,
        reason: str,
    ) -> ComplianceCheckpoint:
        """Mark a checkpoint as requiring human review."""
        checkpoint = await self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        checkpoint.status = CheckpointStatus.REQUIRES_REVIEW
        checkpoint.verification_result = {
            "requires_review": True,
            "reason": reason,
        }

        await self.session.flush()
        return checkpoint
