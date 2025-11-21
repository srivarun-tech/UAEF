"""
UAEF Settlement Service

Service for generating and managing financial settlement signals.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uaef.core.logging import get_logger
from uaef.ledger import EventType, LedgerEventService
from uaef.settlement.models import (
    RecipientType,
    SettlementRule,
    SettlementSignal,
    SettlementStatus,
)

logger = get_logger(__name__)


class SettlementService:
    """Service for managing settlement signals and rules."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_service = LedgerEventService(session)

    async def create_rule(
        self,
        name: str,
        trigger_conditions: dict[str, Any],
        amount_type: str = "fixed",
        fixed_amount: Decimal | None = None,
        amount_formula: str | None = None,
        currency: str = "USD",
        recipient_type: RecipientType = RecipientType.AGENT,
        fixed_recipient_id: str | None = None,
        recipient_selector: str | None = None,
        requires_approval: bool = False,
        approval_threshold: Decimal | None = None,
        workflow_definition_id: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SettlementRule:
        """Create a new settlement rule."""
        rule = SettlementRule(
            name=name,
            description=description,
            workflow_definition_id=workflow_definition_id,
            trigger_conditions=trigger_conditions,
            amount_type=amount_type,
            fixed_amount=fixed_amount,
            amount_formula=amount_formula,
            currency=currency,
            recipient_type=recipient_type.value,
            fixed_recipient_id=fixed_recipient_id,
            recipient_selector=recipient_selector,
            requires_approval=requires_approval,
            approval_threshold=approval_threshold,
            metadata=metadata or {},
        )

        self.session.add(rule)
        await self.session.flush()

        logger.info(
            "settlement_rule_created",
            rule_id=rule.id,
            name=name,
            amount_type=amount_type,
        )

        return rule

    async def get_rule(self, rule_id: str) -> SettlementRule | None:
        """Get a settlement rule by ID."""
        result = await self.session.execute(
            select(SettlementRule).where(SettlementRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get_rule_by_name(self, name: str) -> SettlementRule | None:
        """Get a settlement rule by name."""
        result = await self.session.execute(
            select(SettlementRule).where(SettlementRule.name == name)
        )
        return result.scalar_one_or_none()

    async def list_active_rules(
        self,
        workflow_definition_id: str | None = None,
    ) -> list[SettlementRule]:
        """List active settlement rules, optionally filtered by workflow."""
        query = select(SettlementRule).where(SettlementRule.is_active == True)

        if workflow_definition_id:
            query = query.where(
                (SettlementRule.workflow_definition_id == workflow_definition_id)
                | (SettlementRule.workflow_definition_id == None)
            )

        result = await self.session.execute(query.order_by(SettlementRule.name))
        return list(result.scalars().all())

    async def evaluate_triggers(
        self,
        workflow_execution_id: str,
        workflow_data: dict[str, Any],
    ) -> list[SettlementSignal]:
        """
        Evaluate settlement rules and generate signals for a workflow.

        Args:
            workflow_execution_id: ID of the completed workflow
            workflow_data: Workflow context and output data for evaluation

        Returns:
            List of generated settlement signals
        """
        # Get workflow definition ID from context
        workflow_definition_id = workflow_data.get("definition_id")

        # Get applicable rules
        rules = await self.list_active_rules(workflow_definition_id)

        signals = []
        for rule in rules:
            if await self._evaluate_conditions(rule.trigger_conditions, workflow_data):
                signal = await self._generate_signal(
                    rule=rule,
                    workflow_execution_id=workflow_execution_id,
                    workflow_data=workflow_data,
                )
                signals.append(signal)

        return signals

    async def _evaluate_conditions(
        self,
        conditions: dict[str, Any],
        data: dict[str, Any],
    ) -> bool:
        """
        Evaluate trigger conditions against workflow data.

        Simple condition evaluator supporting basic comparisons.
        """
        if not conditions:
            return True

        # Check all conditions (AND logic)
        for key, expected in conditions.items():
            actual = data.get(key)

            # Handle nested keys with dot notation
            if "." in key:
                parts = key.split(".")
                actual = data
                for part in parts:
                    if isinstance(actual, dict):
                        actual = actual.get(part)
                    else:
                        actual = None
                        break

            # Simple equality check
            if isinstance(expected, dict):
                # Handle operators
                if "$eq" in expected:
                    if actual != expected["$eq"]:
                        return False
                if "$gt" in expected:
                    if actual is None or actual <= expected["$gt"]:
                        return False
                if "$gte" in expected:
                    if actual is None or actual < expected["$gte"]:
                        return False
                if "$lt" in expected:
                    if actual is None or actual >= expected["$lt"]:
                        return False
                if "$lte" in expected:
                    if actual is None or actual > expected["$lte"]:
                        return False
                if "$in" in expected:
                    if actual not in expected["$in"]:
                        return False
            else:
                # Direct equality
                if actual != expected:
                    return False

        return True

    async def _generate_signal(
        self,
        rule: SettlementRule,
        workflow_execution_id: str,
        workflow_data: dict[str, Any],
    ) -> SettlementSignal:
        """Generate a settlement signal from a rule."""
        # Calculate amount
        if rule.amount_type == "fixed":
            amount = rule.fixed_amount or Decimal("0.00")
        elif rule.amount_type == "variable":
            # Get amount from workflow output
            amount = Decimal(str(workflow_data.get("settlement_amount", 0)))
        elif rule.amount_type == "calculated":
            # Evaluate formula (simple eval for now, should use safe evaluator)
            try:
                # Create safe namespace for evaluation
                namespace = {"data": workflow_data, "Decimal": Decimal}
                amount = Decimal(str(eval(rule.amount_formula, {}, namespace)))
            except Exception as e:
                logger.error(
                    "settlement_formula_error",
                    rule_id=rule.id,
                    formula=rule.amount_formula,
                    error=str(e),
                )
                amount = Decimal("0.00")
        else:
            amount = Decimal("0.00")

        # Determine recipient
        if rule.fixed_recipient_id:
            recipient_id = rule.fixed_recipient_id
        elif rule.recipient_selector:
            # Evaluate selector expression
            try:
                namespace = {"data": workflow_data}
                recipient_id = str(eval(rule.recipient_selector, {}, namespace))
            except Exception as e:
                logger.error(
                    "settlement_recipient_error",
                    rule_id=rule.id,
                    selector=rule.recipient_selector,
                    error=str(e),
                )
                recipient_id = "unknown"
        else:
            # Default to primary agent from workflow data
            recipient_id = workflow_data.get("primary_agent_id", "unknown")

        # Determine initial status
        if rule.requires_approval and (
            rule.approval_threshold is None or amount >= rule.approval_threshold
        ):
            status = SettlementStatus.PENDING
        else:
            status = SettlementStatus.APPROVED

        # Create signal
        signal = SettlementSignal(
            workflow_execution_id=workflow_execution_id,
            settlement_rule_id=rule.id,
            amount=amount,
            currency=rule.currency,
            recipient_type=rule.recipient_type,
            recipient_id=recipient_id,
            status=status.value,
            metadata={
                "rule_name": rule.name,
                "workflow_data_keys": list(workflow_data.keys()),
            },
        )

        self.session.add(signal)
        await self.session.flush()

        # Record event
        await self.event_service.record_event(
            event_type=EventType.SETTLEMENT_TRIGGERED,
            payload={
                "signal_id": signal.id,
                "rule_name": rule.name,
                "amount": str(amount),
                "currency": rule.currency,
                "recipient_id": recipient_id,
                "status": status.value,
            },
            workflow_id=workflow_execution_id,
        )

        logger.info(
            "settlement_signal_generated",
            signal_id=signal.id,
            rule_id=rule.id,
            amount=str(amount),
            recipient_id=recipient_id,
        )

        return signal

    async def get_signal(self, signal_id: str) -> SettlementSignal | None:
        """Get a settlement signal by ID."""
        result = await self.session.execute(
            select(SettlementSignal).where(SettlementSignal.id == signal_id)
        )
        return result.scalar_one_or_none()

    async def list_signals(
        self,
        workflow_execution_id: str | None = None,
        status: SettlementStatus | None = None,
        recipient_id: str | None = None,
    ) -> list[SettlementSignal]:
        """List settlement signals with optional filters."""
        query = select(SettlementSignal)

        if workflow_execution_id:
            query = query.where(
                SettlementSignal.workflow_execution_id == workflow_execution_id
            )
        if status:
            query = query.where(SettlementSignal.status == status.value)
        if recipient_id:
            query = query.where(SettlementSignal.recipient_id == recipient_id)

        result = await self.session.execute(
            query.order_by(SettlementSignal.created_at.desc())
        )
        return list(result.scalars().all())

    async def approve_signal(
        self,
        signal_id: str,
        approved_by: str,
    ) -> SettlementSignal:
        """Approve a settlement signal."""
        signal = await self.get_signal(signal_id)
        if not signal:
            raise ValueError(f"Settlement signal {signal_id} not found")

        if signal.status != SettlementStatus.PENDING.value:
            raise ValueError(f"Signal is not pending approval: {signal.status}")

        signal.status = SettlementStatus.APPROVED.value
        signal.approved_by = approved_by
        signal.approved_at = datetime.now(timezone.utc)

        await self.session.flush()

        logger.info(
            "settlement_approved",
            signal_id=signal_id,
            approved_by=approved_by,
        )

        return signal

    async def process_signal(
        self,
        signal_id: str,
        transaction_id: str,
    ) -> SettlementSignal:
        """Mark a settlement signal as processed."""
        signal = await self.get_signal(signal_id)
        if not signal:
            raise ValueError(f"Settlement signal {signal_id} not found")

        if signal.status not in [
            SettlementStatus.APPROVED.value,
            SettlementStatus.PROCESSING.value,
        ]:
            raise ValueError(
                f"Signal must be approved before processing: {signal.status}"
            )

        signal.status = SettlementStatus.COMPLETED.value
        signal.processed_at = datetime.now(timezone.utc)
        signal.transaction_id = transaction_id

        await self.session.flush()

        # Record event
        await self.event_service.record_event(
            event_type=EventType.SETTLEMENT_COMPLETED,
            payload={
                "signal_id": signal_id,
                "transaction_id": transaction_id,
                "amount": str(signal.amount),
                "recipient_id": signal.recipient_id,
            },
            workflow_id=signal.workflow_execution_id,
        )

        logger.info(
            "settlement_processed",
            signal_id=signal_id,
            transaction_id=transaction_id,
        )

        return signal

    async def fail_signal(
        self,
        signal_id: str,
        error_message: str,
    ) -> SettlementSignal:
        """Mark a settlement signal as failed."""
        signal = await self.get_signal(signal_id)
        if not signal:
            raise ValueError(f"Settlement signal {signal_id} not found")

        signal.status = SettlementStatus.FAILED.value
        signal.error_message = error_message
        signal.retry_count += 1

        await self.session.flush()

        # Record event
        await self.event_service.record_event(
            event_type=EventType.SETTLEMENT_FAILED,
            payload={
                "signal_id": signal_id,
                "error": error_message,
                "retry_count": signal.retry_count,
            },
            workflow_id=signal.workflow_execution_id,
        )

        logger.error(
            "settlement_failed",
            signal_id=signal_id,
            error=error_message,
        )

        return signal
