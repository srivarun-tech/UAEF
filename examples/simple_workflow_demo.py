"""
UAEF Simple Workflow Demo

Demonstrates creating an agent, defining a workflow, and executing it.
"""

import asyncio
from decimal import Decimal

from uaef.core import configure_logging, get_session, init_db
from uaef.ledger import EventType, LedgerEventService
from uaef.agents import AgentRegistry, WorkflowService
from uaef.settlement import RecipientType, SettlementService


async def main():
    """Run the demo workflow."""
    # Configure logging
    configure_logging()

    # Initialize database (creates tables if they don't exist)
    print("🔧 Initializing database...")
    await init_db()

    async with get_session() as session:
        print("\n" + "=" * 60)
        print("UAEF Simple Workflow Demo")
        print("=" * 60)

        # Step 1: Register an Agent
        print("\n📝 Step 1: Registering Claude Agent...")
        registry = AgentRegistry(session)

        agent, api_key = await registry.register_agent(
            name="Document Processor",
            description="Processes and analyzes documents",
            capabilities=["document_analysis", "data_extraction"],
            model="claude-sonnet-4-20250514",
            system_prompt="You are a document processing assistant. Extract and analyze document data.",
        )

        print(f"✅ Agent registered: {agent.name}")
        print(f"   ID: {agent.id}")
        print(f"   API Key: {api_key[:20]}... (keep this secure!)")

        # Activate the agent
        await registry.activate_agent(agent.id)
        print(f"✅ Agent activated")

        # Step 2: Create a Workflow Definition
        print("\n📋 Step 2: Creating Workflow Definition...")
        workflow_service = WorkflowService(session)

        workflow_def = await workflow_service.create_definition(
            name="Document Processing Pipeline",
            description="Extracts data from documents and validates it",
            tasks=[
                {
                    "id": "extract",
                    "name": "Extract Document Data",
                    "type": "agent",
                    "config": {
                        "prompt": "Extract key data from the document: invoice number, date, amount, vendor",
                        "capability": "data_extraction",
                    },
                },
                {
                    "id": "validate",
                    "name": "Validate Extracted Data",
                    "type": "agent",
                    "config": {
                        "prompt": "Validate the extracted data for completeness and correctness",
                        "capability": "document_analysis",
                    },
                },
                {
                    "id": "approval",
                    "name": "Human Approval",
                    "type": "human_approval",
                    "config": {
                        "description": "Review and approve the processed document",
                    },
                },
            ],
            edges=[
                {"from": "extract", "to": "validate"},
                {"from": "validate", "to": "approval"},
            ],
        )

        print(f"✅ Workflow created: {workflow_def.name}")
        print(f"   ID: {workflow_def.id}")
        print(f"   Tasks: {len(workflow_def.tasks)}")

        # Step 3: Create a Settlement Rule
        print("\n💰 Step 3: Creating Settlement Rule...")
        settlement_service = SettlementService(session)

        settlement_rule = await settlement_service.create_rule(
            name="document_processing_fee",
            description="Payment for document processing",
            trigger_conditions={
                "status": "completed",
                "tasks_completed": {"$gte": 2},
            },
            amount_type="fixed",
            fixed_amount=Decimal("50.00"),
            currency="USD",
            recipient_type=RecipientType.AGENT,
            requires_approval=False,
        )

        print(f"✅ Settlement rule created: {settlement_rule.name}")
        print(f"   Amount: ${settlement_rule.fixed_amount} {settlement_rule.currency}")

        # Step 4: Start Workflow Execution
        print("\n🚀 Step 4: Starting Workflow Execution...")

        # Note: In real usage, you would have Claude API key configured
        # For demo, we'll show the workflow start but it will pause
        # waiting for agent execution

        execution = await workflow_service.start_workflow(
            definition_id=workflow_def.id,
            input_data={
                "document_url": "https://example.com/invoice.pdf",
                "document_type": "invoice",
            },
            name="Demo Document Processing",
            initiated_by="demo-user",
            initiated_by_type="user",
        )

        print(f"✅ Workflow started: {execution.name}")
        print(f"   Execution ID: {execution.id}")
        print(f"   Status: {execution.status}")
        print(f"   Total Tasks: {execution.total_tasks}")

        # Step 5: Check Ledger Events
        print("\n📊 Step 5: Checking Ledger Events...")
        event_service = LedgerEventService(session)

        events = await event_service.get_events_by_workflow(
            workflow_id=execution.id,
            limit=10,
        )

        print(f"✅ Found {len(events)} events in ledger:")
        for event in events:
            print(f"   - {event.event_type}: Seq #{event.sequence_number}")

        # Step 6: View Agent Metrics
        print("\n📈 Step 6: Agent Metrics...")
        updated_agent = await registry.get_agent(agent.id)
        print(f"✅ Agent: {updated_agent.name}")
        print(f"   Total Tasks: {updated_agent.total_tasks}")
        print(f"   Successful: {updated_agent.successful_tasks}")
        print(f"   Failed: {updated_agent.failed_tasks}")

        print("\n" + "=" * 60)
        print("Demo Complete!")
        print("=" * 60)

        print("\n⚠️  Note: The workflow is running but will need:")
        print("   1. UAEF_AGENT_ANTHROPIC_API_KEY configured in .env")
        print("   2. Tasks will execute asynchronously via agents")
        print("   3. Human approval task will wait for manual approval")

        print("\n💡 Next Steps:")
        print("   1. Configure your Anthropic API key in .env")
        print("   2. Run: python examples/complete_workflow_demo.py")
        print("   3. Monitor workflows via: python examples/workflow_monitor.py")

        return {
            "agent": agent,
            "workflow_def": workflow_def,
            "execution": execution,
            "settlement_rule": settlement_rule,
        }


if __name__ == "__main__":
    result = asyncio.run(main())
    print("\n✅ Demo completed successfully!")
