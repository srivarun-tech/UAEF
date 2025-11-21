"""
UAEF Workflow Monitor

Monitor workflow executions and view their status.
"""

import asyncio
from datetime import datetime, timezone

from uaef.core import configure_logging, get_session
from uaef.ledger import AuditTrailService, LedgerEventService
from uaef.agents.models import TaskStatus, WorkflowExecution, WorkflowStatus
from uaef.settlement import SettlementService
from sqlalchemy import select


async def list_workflows():
    """List all workflow executions."""
    async with get_session() as session:
        result = await session.execute(
            select(WorkflowExecution).order_by(WorkflowExecution.created_at.desc()).limit(10)
        )
        workflows = list(result.scalars().all())

        print("\n" + "=" * 80)
        print("Recent Workflow Executions")
        print("=" * 80)

        if not workflows:
            print("No workflows found. Run simple_workflow_demo.py first!")
            return

        for wf in workflows:
            status_emoji = {
                WorkflowStatus.RUNNING.value: "🔄",
                WorkflowStatus.COMPLETED.value: "✅",
                WorkflowStatus.FAILED.value: "❌",
                WorkflowStatus.PENDING.value: "⏸️",
            }.get(wf.status, "❓")

            print(f"\n{status_emoji} {wf.name}")
            print(f"   ID: {wf.id}")
            print(f"   Status: {wf.status}")
            print(f"   Progress: {wf.completed_tasks}/{wf.total_tasks} tasks")
            print(f"   Started: {wf.started_at or 'Not started'}")
            if wf.completed_at:
                duration = wf.completed_at - wf.started_at
                print(f"   Duration: {duration}")


async def view_workflow_details(workflow_id: str):
    """View detailed information about a workflow."""
    async with get_session() as session:
        # Get workflow
        result = await session.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()

        if not workflow:
            print(f"❌ Workflow {workflow_id} not found")
            return

        print("\n" + "=" * 80)
        print(f"Workflow Details: {workflow.name}")
        print("=" * 80)

        print(f"\n📋 Basic Info:")
        print(f"   ID: {workflow.id}")
        print(f"   Definition ID: {workflow.definition_id}")
        print(f"   Status: {workflow.status}")
        print(f"   Progress: {workflow.completed_tasks}/{workflow.total_tasks}")

        if workflow.started_at:
            print(f"   Started: {workflow.started_at}")
        if workflow.completed_at:
            print(f"   Completed: {workflow.completed_at}")
            duration = workflow.completed_at - workflow.started_at
            print(f"   Duration: {duration}")

        # Get tasks
        from uaef.agents.models import TaskExecution

        result = await session.execute(
            select(TaskExecution)
            .where(TaskExecution.workflow_execution_id == workflow_id)
            .order_by(TaskExecution.created_at)
        )
        tasks = list(result.scalars().all())

        print(f"\n📝 Tasks ({len(tasks)}):")
        for task in tasks:
            status_emoji = {
                TaskStatus.PENDING.value: "⏸️",
                TaskStatus.RUNNING.value: "🔄",
                TaskStatus.COMPLETED.value: "✅",
                TaskStatus.FAILED.value: "❌",
                TaskStatus.WAITING_INPUT.value: "⏳",
            }.get(task.status, "❓")

            print(f"   {status_emoji} {task.task_name}")
            print(f"      Status: {task.status}")
            print(f"      Type: {task.task_type}")
            if task.agent_id:
                print(f"      Agent: {task.agent_id}")
            if task.started_at:
                print(f"      Started: {task.started_at}")
            if task.completed_at:
                print(f"      Completed: {task.completed_at}")
            if task.error_message:
                print(f"      Error: {task.error_message}")

        # Get ledger events
        event_service = LedgerEventService(session)
        events = await event_service.get_events_by_workflow(workflow_id, limit=20)

        print(f"\n📊 Ledger Events ({len(events)}):")
        for event in events[:10]:  # Show first 10
            print(f"   - Seq #{event.sequence_number}: {event.event_type}")
            print(f"     Time: {event.created_at}")

        # Check settlements
        settlement_service = SettlementService(session)
        signals = await settlement_service.list_signals(workflow_execution_id=workflow_id)

        if signals:
            print(f"\n💰 Settlement Signals ({len(signals)}):")
            for signal in signals:
                print(f"   - Amount: ${signal.amount} {signal.currency}")
                print(f"     Recipient: {signal.recipient_id}")
                print(f"     Status: {signal.status}")


async def view_agent_stats():
    """View statistics for all agents."""
    async with get_session() as session:
        from uaef.agents.models import Agent

        result = await session.execute(
            select(Agent).order_by(Agent.name)
        )
        agents = list(result.scalars().all())

        print("\n" + "=" * 80)
        print("Agent Statistics")
        print("=" * 80)

        if not agents:
            print("No agents found. Run simple_workflow_demo.py first!")
            return

        for agent in agents:
            success_rate = (
                (agent.successful_tasks / agent.total_tasks * 100)
                if agent.total_tasks > 0
                else 0
            )

            print(f"\n🤖 {agent.name}")
            print(f"   ID: {agent.id}")
            print(f"   Type: {agent.agent_type}")
            print(f"   Status: {agent.status}")
            print(f"   Model: {agent.model or 'N/A'}")
            print(f"   Capabilities: {', '.join(agent.capabilities)}")
            print(f"   Total Tasks: {agent.total_tasks}")
            print(f"   Successful: {agent.successful_tasks}")
            print(f"   Failed: {agent.failed_tasks}")
            print(f"   Success Rate: {success_rate:.1f}%")


async def view_settlement_dashboard():
    """View settlement signals and rules."""
    async with get_session() as session:
        settlement_service = SettlementService(session)

        # Get all rules
        rules = await settlement_service.list_active_rules()

        print("\n" + "=" * 80)
        print("Settlement Dashboard")
        print("=" * 80)

        print(f"\n💰 Active Rules ({len(rules)}):")
        for rule in rules:
            print(f"\n   📋 {rule.name}")
            print(f"      Amount: {rule.amount_type}")
            if rule.fixed_amount:
                print(f"      Fixed: ${rule.fixed_amount} {rule.currency}")
            print(f"      Recipient: {rule.recipient_type}")
            print(f"      Approval: {'Required' if rule.requires_approval else 'Auto'}")

        # Get recent signals
        from uaef.settlement.models import SettlementSignal

        result = await session.execute(
            select(SettlementSignal)
            .order_by(SettlementSignal.created_at.desc())
            .limit(10)
        )
        signals = list(result.scalars().all())

        print(f"\n💸 Recent Signals ({len(signals)}):")
        for signal in signals:
            status_emoji = {
                "pending": "⏸️",
                "approved": "✅",
                "processing": "🔄",
                "completed": "💰",
                "failed": "❌",
            }.get(signal.status, "❓")

            print(f"   {status_emoji} ${signal.amount} {signal.currency}")
            print(f"      Recipient: {signal.recipient_id}")
            print(f"      Status: {signal.status}")
            print(f"      Created: {signal.created_at}")


async def interactive_menu():
    """Interactive monitoring menu."""
    configure_logging()

    while True:
        print("\n" + "=" * 80)
        print("UAEF Workflow Monitor")
        print("=" * 80)
        print("\n1. List Recent Workflows")
        print("2. View Workflow Details")
        print("3. Agent Statistics")
        print("4. Settlement Dashboard")
        print("5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            await list_workflows()
        elif choice == "2":
            workflow_id = input("Enter workflow ID: ").strip()
            await view_workflow_details(workflow_id)
        elif choice == "3":
            await view_agent_stats()
        elif choice == "4":
            await view_settlement_dashboard()
        elif choice == "5":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    asyncio.run(interactive_menu())
