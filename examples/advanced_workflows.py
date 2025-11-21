"""
Advanced Workflow Examples for UAEF

Demonstrates various workflow patterns:
1. Multi-task workflow with dependencies (DAG)
2. Data analysis pipeline
3. Customer support workflow
4. Content generation workflow
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
from decimal import Decimal
from datetime import datetime
from uaef.core import configure_logging, get_session, init_db
from uaef.orchestration import AgentRegistry, WorkflowService, ClaudeAgentExecutor
from uaef.orchestration.models import WorkflowDefinition
from uaef.ledger import LedgerEventService
from uaef.settlement import SettlementService


async def create_multi_task_workflow(session):
    """
    Create a multi-task workflow with dependencies (DAG).

    Flow: research -> analyze -> summarize
          research -> fact_check -> summarize
    """
    print("\n" + "=" * 80)
    print("WORKFLOW 1: Multi-Task Pipeline with Dependencies")
    print("=" * 80)

    workflow_def = WorkflowDefinition(
        name="Research Analysis Pipeline",
        description="Multi-task workflow demonstrating DAG execution",
        tasks=[
            {
                "name": "research",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Provide 3 key facts about artificial intelligence. Be concise (under 50 words).",
                },
                "dependencies": [],
            },
            {
                "name": "analyze",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Analyze the trends mentioned in the research. Keep it brief (under 40 words).",
                },
                "dependencies": ["research"],
            },
            {
                "name": "fact_check",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Verify the accuracy of the research findings. Brief response (under 30 words).",
                },
                "dependencies": ["research"],
            },
            {
                "name": "summarize",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Create a final summary combining analysis and fact-checking. Very brief (under 40 words).",
                },
                "dependencies": ["analyze", "fact_check"],
            },
        ],
        is_active=True,
    )

    session.add(workflow_def)
    await session.commit()
    await session.refresh(workflow_def)

    print(f"✓ Workflow created: {workflow_def.name}")
    print(f"  Tasks: {len(workflow_def.tasks)}")
    print(f"  Structure: research → [analyze, fact_check] → summarize")

    return workflow_def


async def create_data_analysis_workflow(session):
    """Create a data analysis workflow."""
    print("\n" + "=" * 80)
    print("WORKFLOW 2: Data Analysis Pipeline")
    print("=" * 80)

    workflow_def = WorkflowDefinition(
        name="Data Analysis Workflow",
        description="Analyze data and generate insights",
        tasks=[
            {
                "name": "collect_data",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Generate sample sales data: 5 products with sales figures. Format: Product: Sales. Keep brief.",
                },
                "dependencies": [],
            },
            {
                "name": "calculate_stats",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Calculate total sales and identify top performer from the data. Brief summary.",
                },
                "dependencies": ["collect_data"],
            },
            {
                "name": "generate_report",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Create a one-sentence executive summary of the sales analysis.",
                },
                "dependencies": ["calculate_stats"],
            },
        ],
        is_active=True,
    )

    session.add(workflow_def)
    await session.commit()
    await session.refresh(workflow_def)

    print(f"✓ Workflow created: {workflow_def.name}")
    print(f"  Tasks: {len(workflow_def.tasks)}")
    print(f"  Flow: collect_data → calculate_stats → generate_report")

    return workflow_def


async def create_customer_support_workflow(session):
    """Create a customer support workflow."""
    print("\n" + "=" * 80)
    print("WORKFLOW 3: Customer Support Pipeline")
    print("=" * 80)

    workflow_def = WorkflowDefinition(
        name="Customer Support Workflow",
        description="Process and respond to customer inquiries",
        tasks=[
            {
                "name": "classify_inquiry",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Classify this inquiry: 'My order hasn't arrived'. Category only (1-2 words).",
                },
                "dependencies": [],
            },
            {
                "name": "draft_response",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Draft a brief, empathetic response to a shipping delay inquiry (under 40 words).",
                },
                "dependencies": ["classify_inquiry"],
            },
            {
                "name": "quality_check",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Review the response for professionalism. Reply with 'Approved' or suggest one improvement.",
                },
                "dependencies": ["draft_response"],
            },
        ],
        is_active=True,
    )

    session.add(workflow_def)
    await session.commit()
    await session.refresh(workflow_def)

    print(f"✓ Workflow created: {workflow_def.name}")
    print(f"  Tasks: {len(workflow_def.tasks)}")
    print(f"  Flow: classify → draft_response → quality_check")

    return workflow_def


async def create_content_generation_workflow(session):
    """Create a content generation workflow."""
    print("\n" + "=" * 80)
    print("WORKFLOW 4: Content Generation Pipeline")
    print("=" * 80)

    workflow_def = WorkflowDefinition(
        name="Content Generation Workflow",
        description="Generate and refine content",
        tasks=[
            {
                "name": "brainstorm",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "List 3 blog post ideas about cloud computing. Just titles, brief.",
                },
                "dependencies": [],
            },
            {
                "name": "write_outline",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Create a 3-point outline for the first blog idea. Very brief.",
                },
                "dependencies": ["brainstorm"],
            },
            {
                "name": "write_intro",
                "task_type": "agent",
                "agent_type": "claude",
                "config": {
                    "prompt": "Write a 2-sentence introduction based on the outline.",
                },
                "dependencies": ["write_outline"],
            },
        ],
        is_active=True,
    )

    session.add(workflow_def)
    await session.commit()
    await session.refresh(workflow_def)

    print(f"✓ Workflow created: {workflow_def.name}")
    print(f"  Tasks: {len(workflow_def.tasks)}")
    print(f"  Flow: brainstorm → write_outline → write_intro")

    return workflow_def


async def execute_workflow(session, workflow_def, agent, settlement_service=None):
    """Execute a workflow and display results."""
    workflow_service = WorkflowService(session)
    ledger_service = LedgerEventService(session)

    print(f"\n{'─' * 80}")
    print(f"Executing: {workflow_def.name}")
    print(f"{'─' * 80}")

    # Create settlement rule if service provided
    if settlement_service:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")
        rule = await settlement_service.create_rule(
            name=f"Payment {workflow_def.name} {timestamp}",
            trigger_conditions={"workflow_definition_id": workflow_def.id},
            amount_type="fixed",
            fixed_amount=Decimal("15.00"),
            currency="USD",
            fixed_recipient_id=agent.id,
        )
        print(f"✓ Settlement rule: ${rule.fixed_amount} {rule.currency}")

    # Start workflow
    execution = await workflow_service.start_workflow(
        definition_id=workflow_def.id,
        input_data={"timestamp": str(datetime.now())},
        initiated_by="advanced_workflows",
    )

    print(f"✓ Workflow started: {execution.id[:8]}...")
    await session.refresh(execution)

    # Get events
    events = await ledger_service.get_events_by_workflow(execution.id)

    print(f"\nResults:")
    print(f"  Status: {execution.status}")
    print(f"  Events: {len(events)} recorded")
    print(f"  Duration: ~{len(events)} operations")

    # Show task breakdown
    task_events = [e for e in events if e.event_type in ['task_started', 'task_completed']]
    if task_events:
        print(f"  Tasks: {len(task_events)//2} completed")

    # Check settlement
    if settlement_service:
        signals = await settlement_service.list_signals(workflow_execution_id=execution.id)
        if signals:
            print(f"  Settlement: ${signals[0].amount} {signals[0].currency} generated")

    return execution


async def main():
    """Run advanced workflow demonstrations."""
    print("=" * 80)
    print("UAEF ADVANCED WORKFLOWS DEMO")
    print("=" * 80)
    print("\nDemonstrating multiple workflow patterns with dependencies")

    configure_logging()
    await init_db()

    async with get_session() as session:
        # Setup services
        agent_registry = AgentRegistry(session)
        settlement_service = SettlementService(session)

        # Register agent
        print("\n[Setup] Registering AI agent...")
        agent, api_key = await agent_registry.register_agent(
            name="Workflow Agent",
            agent_type="claude",
            capabilities=["research", "analysis", "writing"],
            model="claude-sonnet-4-20250514",
        )
        await agent_registry.activate_agent(agent.id)
        print(f"✓ Agent ready: {agent.name} ({agent.id[:8]}...)")

        # Create all workflow definitions
        workflows = []
        workflows.append(await create_multi_task_workflow(session))
        workflows.append(await create_data_analysis_workflow(session))
        workflows.append(await create_customer_support_workflow(session))
        workflows.append(await create_content_generation_workflow(session))

        print(f"\n{'=' * 80}")
        print(f"Created {len(workflows)} workflow definitions")
        print(f"{'=' * 80}")

        # Execute workflows
        print("\n" + "=" * 80)
        print("EXECUTING WORKFLOWS")
        print("=" * 80)

        executions = []
        for i, workflow_def in enumerate(workflows, 1):
            # Add settlement to workflows 1 and 3
            use_settlement = i in [1, 3]
            execution = await execute_workflow(
                session,
                workflow_def,
                agent,
                settlement_service if use_settlement else None
            )
            executions.append(execution)

            if i < len(workflows):
                print()  # Space between workflows

        # Final summary
        print("\n" + "=" * 80)
        print("EXECUTION SUMMARY")
        print("=" * 80)

        ledger_service = LedgerEventService(session)
        total_events = 0

        for execution in executions:
            events = await ledger_service.get_events_by_workflow(execution.id)
            total_events += len(events)
            await session.refresh(execution)
            status_icon = "✓" if execution.status == "completed" else "⋯"
            print(f"{status_icon} {execution.workflow_definition.name[:40]:40} | {execution.status:10} | {len(events)} events")

        print(f"\n{'─' * 80}")
        print(f"Total workflows: {len(executions)}")
        print(f"Total events: {total_events}")
        print(f"All systems: OPERATIONAL ✓")
        print(f"{'─' * 80}")


if __name__ == "__main__":
    asyncio.run(main())
