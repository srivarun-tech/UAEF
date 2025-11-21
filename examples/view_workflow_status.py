"""
UAEF Workflow Status Viewer (Non-Interactive)

Quick view of workflow execution status for testing.
"""

import asyncio
from datetime import datetime

from sqlalchemy import select

from uaef.core import configure_logging, get_session
from uaef.ledger import LedgerEventService
from uaef.agents import AgentRegistry
from uaef.agents.models import WorkflowDefinition, WorkflowExecution
from uaef.agents.workflow import WorkflowService
from uaef.settlement import SettlementService
from uaef.settlement.models import SettlementSignal, SettlementRule


async def main():
    configure_logging()

    print("\n" + "="*80)
    print("UAEF Workflow Status Report")
    print("="*80)

    async with get_session() as session:
        workflow_service = WorkflowService(session)
        agent_registry = AgentRegistry(session)
        ledger_service = LedgerEventService(session)
        settlement_service = SettlementService(session)

        # 1. List all workflow executions
        print("\n📋 WORKFLOW EXECUTIONS")
        print("-" * 80)

        result = await session.execute(
            select(WorkflowExecution).order_by(WorkflowExecution.created_at.desc()).limit(10)
        )
        executions = result.scalars().all()

        if not executions:
            print("No workflow executions found.")
        else:
            for execution in executions:
                definition = await workflow_service.get_definition(execution.definition_id)

                print(f"\n🔹 Workflow: {definition.name}")
                print(f"   Execution ID: {execution.id}")
                print(f"   Status: {execution.status}")
                print(f"   Started: {execution.started_at}")
                print(f"   Progress: {execution.completed_tasks}/{execution.total_tasks} tasks")

                if execution.context:
                    print(f"   Context: {execution.context}")

        # 2. Show agents
        print("\n\n🤖 REGISTERED AGENTS")
        print("-" * 80)

        agents = await agent_registry.list_agents()

        if not agents:
            print("No agents registered.")
        else:
            for agent in agents:
                print(f"\n🔹 {agent.name}")
                print(f"   ID: {agent.id}")
                print(f"   Type: {agent.agent_type}")
                print(f"   Status: {agent.status}")
                print(f"   Capabilities: {', '.join(agent.capabilities)}")
                print(f"   Tasks: {agent.total_tasks} (Success: {agent.successful_tasks}, Failed: {agent.failed_tasks})")

        # 3. Show recent ledger events
        print("\n\n📜 RECENT LEDGER EVENTS")
        print("-" * 80)

        latest_seq = await ledger_service.get_latest_sequence()

        if latest_seq == 0:
            print("No events in ledger.")
        else:
            # Get last 10 events
            start = max(1, latest_seq - 9)
            events = await ledger_service.get_event_chain(start, latest_seq)

            for event in events:
                print(f"\n#{event.sequence_number} - {event.event_type}")
                print(f"   ID: {event.id}")
                print(f"   Time: {event.created_at}")
                if event.workflow_id:
                    print(f"   Workflow: {event.workflow_id}")
                if event.agent_id:
                    print(f"   Agent: {event.agent_id}")
                if event.payload:
                    print(f"   Payload: {event.payload}")

        # 4. Show settlement signals
        print("\n\n💰 SETTLEMENT SIGNALS")
        print("-" * 80)

        result = await session.execute(
            select(SettlementSignal).order_by(SettlementSignal.created_at.desc()).limit(10)
        )
        signals = result.scalars().all()

        if not signals:
            print("No settlement signals generated.")
        else:
            for signal in signals:
                print(f"\n🔹 Signal ID: {signal.id}")
                print(f"   Amount: {signal.amount} {signal.currency}")
                print(f"   Status: {signal.status}")
                print(f"   Recipient: {signal.recipient_type} - {signal.recipient_id}")
                print(f"   Workflow: {signal.workflow_execution_id}")
                if signal.approved_at:
                    print(f"   Approved: {signal.approved_at}")
                if signal.processed_at:
                    print(f"   Processed: {signal.processed_at}")

        # 5. Show settlement rules
        print("\n\n📏 SETTLEMENT RULES")
        print("-" * 80)

        result = await session.execute(
            select(SettlementRule).order_by(SettlementRule.created_at.desc())
        )
        rules = result.scalars().all()

        if not rules:
            print("No settlement rules configured.")
        else:
            for rule in rules:
                print(f"\n🔹 {rule.name}")
                print(f"   ID: {rule.id}")
                print(f"   Active: {rule.is_active}")
                print(f"   Amount Type: {rule.amount_type}")
                if rule.fixed_amount:
                    print(f"   Fixed Amount: {rule.fixed_amount} {rule.currency}")
                print(f"   Recipient Type: {rule.recipient_type}")
                if rule.requires_approval:
                    print(f"   Requires Approval: Yes (threshold: {rule.approval_threshold})")

        print("\n" + "="*80)
        print("End of Report")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
