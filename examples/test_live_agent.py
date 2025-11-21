"""
Test UAEF with Live Claude Agent

Quick test to verify the system works with a real Anthropic API key.
"""

import asyncio

from uaef.core import configure_logging, get_session
from uaef.ledger import EventType, LedgerEventService
from uaef.agents import AgentRegistry, ClaudeAgentExecutor
from uaef.agents.models import AgentStatus, WorkflowDefinition
from uaef.agents.workflow import WorkflowService
from uaef.settlement import SettlementService


async def main():
    configure_logging()

    print("\n" + "="*80)
    print("UAEF Live Agent Test")
    print("="*80)

    async with get_session() as session:
        # Services
        agent_registry = AgentRegistry(session)
        agent_executor = ClaudeAgentExecutor(session)
        workflow_service = WorkflowService(session)
        settlement_service = SettlementService(session)
        ledger_service = LedgerEventService(session)

        # 1. Register a Claude agent
        print("\n🤖 Step 1: Registering Claude Agent...")
        agent, api_key = await agent_registry.register_agent(
            name="Test Assistant",
            agent_type="claude",
            capabilities=["analysis", "summarization"],
        )
        await agent_registry.activate_agent(agent.id)
        print(f"✅ Agent registered: {agent.name} (ID: {agent.id[:8]}...)")
        print(f"   API Key: {api_key[:20]}... (keep secure)")

        # 2. Test direct agent invocation
        print("\n💬 Step 2: Testing Agent Invocation...")
        try:
            response = await agent_executor.invoke(
                agent=agent,
                prompt="Please respond with a simple greeting. Keep it under 20 words.",
                context={},
            )
            print(f"✅ Agent Response: {response['content'][:100]}...")
        except Exception as e:
            print(f"❌ Agent invocation failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # 3. Create a simple workflow
        print("\n📋 Step 3: Creating Simple Workflow...")
        workflow_def = WorkflowDefinition(
            name="Quick Analysis Workflow",
            description="Simple workflow for testing",
            tasks=[
                {
                    "name": "analyze",
                    "task_type": "agent",
                    "agent_type": "claude",
                    "config": {
                        "prompt": "Analyze this: The system is operational.",
                        "max_tokens": 100,
                    },
                    "dependencies": [],
                }
            ],
        )
        session.add(workflow_def)
        await session.commit()
        await session.refresh(workflow_def)
        print(f"✅ Workflow created: {workflow_def.name}")

        # 4. Create settlement rule
        print("\n💰 Step 4: Creating Settlement Rule...")
        from uaef.settlement.models import RecipientType
        rule = await settlement_service.create_rule(
            name="test_completion_fee",
            workflow_definition_id=workflow_def.id,
            trigger_conditions={"status": {"$eq": "completed"}},
            amount_type="fixed",
            fixed_amount=25.00,
            currency="USD",
            recipient_type=RecipientType.AGENT,
        )
        print(f"✅ Settlement rule: {rule.name} - ${rule.fixed_amount} {rule.currency}")

        # 5. Start workflow
        print("\n🚀 Step 5: Starting Workflow...")
        execution = await workflow_service.start_workflow(
            definition_id=workflow_def.id,
            input_data={"test": "data"},
            initiated_by="test_user",
        )
        print(f"✅ Workflow started: {execution.id[:8]}...")

        # 6. Execute tasks (simulate task completion)
        print("\n⏳ Step 6: Executing Tasks...")
        await asyncio.sleep(1)  # Brief pause

        # Get ready tasks
        scheduler = workflow_service.task_scheduler
        ready_tasks = await scheduler.get_ready_tasks(execution.id)

        if ready_tasks:
            task = ready_tasks[0]
            print(f"   Processing task: {task.task_name}")

            try:
                # Invoke agent for the task
                result = await agent_executor.invoke(
                    agent=agent,
                    prompt=task.config.get("prompt", "Process this task"),
                    context={"task_id": task.id},
                    workflow_id=execution.id,
                )

                # Complete the task
                await workflow_service.complete_task(
                    task_id=task.id,
                    output_data={"result": result.get("content", "")},
                )
                print(f"✅ Task completed successfully")

                # Refresh execution
                await session.refresh(execution)

            except Exception as e:
                print(f"❌ Task execution error: {e}")

        # 7. Check ledger events
        print("\n📜 Step 7: Checking Ledger Events...")
        latest_seq = await ledger_service.get_latest_sequence()
        print(f"✅ Total events in ledger: {latest_seq}")

        # Get last few events
        if latest_seq > 0:
            recent_events = await ledger_service.get_event_chain(
                max(1, latest_seq - 4), latest_seq
            )
            for event in recent_events[-5:]:
                print(f"   - {event.event_type} (seq #{event.sequence_number})")

        # 8. Check agent metrics
        print("\n📊 Step 8: Agent Metrics...")
        await session.refresh(agent)
        print(f"✅ Agent: {agent.name}")
        print(f"   Total tasks: {agent.total_tasks}")
        print(f"   Successful: {agent.successful_tasks}")
        print(f"   Failed: {agent.failed_tasks}")

        # 9. Check workflow status
        print("\n📈 Step 9: Workflow Status...")
        await session.refresh(execution)
        print(f"✅ Workflow: {execution.status}")
        print(f"   Progress: {execution.completed_tasks}/{execution.total_tasks} tasks")

        print("\n" + "="*80)
        print("Test Complete!")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
