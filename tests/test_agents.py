"""
Tests for UAEF Agent Registry Module

Tests for AgentRegistry and ClaudeAgentExecutor.
"""

from unittest.mock import MagicMock, patch

import pytest

from uaef.orchestration.agents import AgentRegistry, ClaudeAgentExecutor
from uaef.orchestration.models import Agent, AgentStatus


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    @pytest.mark.asyncio
    async def test_register_agent(self, session):
        """Test registering a new agent."""
        registry = AgentRegistry(session)

        agent, api_key = await registry.register_agent(
            name="Test Agent",
            description="A test agent",
            capabilities=["read", "write"],
            model="claude-sonnet-4-20250514",
            system_prompt="You are a test agent.",
        )

        assert agent.id is not None
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent"
        assert agent.agent_type == "claude"
        assert agent.capabilities == ["read", "write"]
        assert agent.model == "claude-sonnet-4-20250514"
        assert agent.system_prompt == "You are a test agent."
        assert agent.status == AgentStatus.REGISTERED
        assert agent.api_key_hash is not None
        assert api_key.startswith("uaef_")

    @pytest.mark.asyncio
    async def test_register_agent_with_tools(self, session):
        """Test registering an agent with tools."""
        registry = AgentRegistry(session)

        tools = [
            {
                "name": "search",
                "description": "Search the web",
                "input_schema": {"type": "object"},
            }
        ]

        agent, _ = await registry.register_agent(
            name="Tool Agent",
            tools=tools,
        )

        assert agent.tools == tools

    @pytest.mark.asyncio
    async def test_get_agent(self, session):
        """Test retrieving an agent by ID."""
        registry = AgentRegistry(session)

        created, _ = await registry.register_agent(name="Get Test Agent")
        retrieved = await registry.get_agent(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Get Test Agent"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, session):
        """Test retrieving a non-existent agent returns None."""
        registry = AgentRegistry(session)

        result = await registry.get_agent("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_agent_by_name(self, session):
        """Test retrieving an agent by name."""
        registry = AgentRegistry(session)

        await registry.register_agent(name="Named Agent")
        retrieved = await registry.get_agent_by_name("Named Agent")

        assert retrieved is not None
        assert retrieved.name == "Named Agent"

    @pytest.mark.asyncio
    async def test_list_agents(self, session):
        """Test listing all agents."""
        registry = AgentRegistry(session)

        await registry.register_agent(name="Agent 1")
        await registry.register_agent(name="Agent 2")
        await registry.register_agent(name="Agent 3")

        agents = await registry.list_agents()

        assert len(agents) == 3

    @pytest.mark.asyncio
    async def test_list_agents_by_status(self, session):
        """Test filtering agents by status."""
        registry = AgentRegistry(session)

        agent1, _ = await registry.register_agent(name="Active Agent")
        await registry.register_agent(name="Inactive Agent")

        await registry.activate_agent(agent1.id)

        active_agents = await registry.list_agents(status=AgentStatus.ACTIVE)
        registered_agents = await registry.list_agents(status=AgentStatus.REGISTERED)

        assert len(active_agents) == 1
        assert len(registered_agents) == 1

    @pytest.mark.asyncio
    async def test_list_agents_by_type(self, session):
        """Test filtering agents by type."""
        registry = AgentRegistry(session)

        await registry.register_agent(name="Claude Agent", agent_type="claude")
        await registry.register_agent(name="Custom Agent", agent_type="custom")

        claude_agents = await registry.list_agents(agent_type="claude")
        custom_agents = await registry.list_agents(agent_type="custom")

        assert len(claude_agents) == 1
        assert len(custom_agents) == 1

    @pytest.mark.asyncio
    async def test_list_agents_by_capability(self, session):
        """Test filtering agents by capability."""
        registry = AgentRegistry(session)

        await registry.register_agent(
            name="Reader",
            capabilities=["read"],
        )
        await registry.register_agent(
            name="Writer",
            capabilities=["write"],
        )
        await registry.register_agent(
            name="Full Access",
            capabilities=["read", "write"],
        )

        readers = await registry.list_agents(capability="read")
        writers = await registry.list_agents(capability="write")

        assert len(readers) == 2
        assert len(writers) == 2

    @pytest.mark.asyncio
    async def test_activate_agent(self, session):
        """Test activating an agent."""
        registry = AgentRegistry(session)

        agent, _ = await registry.register_agent(name="To Activate")
        assert agent.status == AgentStatus.REGISTERED

        activated = await registry.activate_agent(agent.id)
        assert activated.status == AgentStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_activate_agent_not_found(self, session):
        """Test activating a non-existent agent raises error."""
        registry = AgentRegistry(session)

        with pytest.raises(ValueError, match="not found"):
            await registry.activate_agent("non-existent")

    @pytest.mark.asyncio
    async def test_deactivate_agent(self, session):
        """Test deactivating an agent."""
        registry = AgentRegistry(session)

        agent, _ = await registry.register_agent(name="To Deactivate")
        await registry.activate_agent(agent.id)
        deactivated = await registry.deactivate_agent(agent.id)

        assert deactivated.status == AgentStatus.DEACTIVATED

    @pytest.mark.asyncio
    async def test_update_agent_status(self, session):
        """Test updating agent status directly."""
        registry = AgentRegistry(session)

        agent, _ = await registry.register_agent(name="Status Update")
        updated = await registry.update_agent_status(agent.id, AgentStatus.BUSY)

        assert updated.status == AgentStatus.BUSY

    @pytest.mark.asyncio
    async def test_update_agent_metrics_success(self, session):
        """Test updating agent metrics for successful task."""
        registry = AgentRegistry(session)

        agent, _ = await registry.register_agent(name="Metrics Agent")
        await registry.update_agent_metrics(agent.id, success=True)

        updated = await registry.get_agent(agent.id)
        assert updated.total_tasks == 1
        assert updated.successful_tasks == 1
        assert updated.failed_tasks == 0

    @pytest.mark.asyncio
    async def test_update_agent_metrics_failure(self, session):
        """Test updating agent metrics for failed task."""
        registry = AgentRegistry(session)

        agent, _ = await registry.register_agent(name="Failed Metrics Agent")
        await registry.update_agent_metrics(agent.id, success=False)

        updated = await registry.get_agent(agent.id)
        assert updated.total_tasks == 1
        assert updated.successful_tasks == 0
        assert updated.failed_tasks == 1

    @pytest.mark.asyncio
    async def test_verify_agent_key(self, session):
        """Test verifying an agent's API key."""
        registry = AgentRegistry(session)

        agent, api_key = await registry.register_agent(name="Key Agent")

        assert await registry.verify_agent_key(agent.id, api_key) is True
        assert await registry.verify_agent_key(agent.id, "wrong-key") is False

    @pytest.mark.asyncio
    async def test_find_available_agent(self, session):
        """Test finding an available agent."""
        registry = AgentRegistry(session)

        agent, _ = await registry.register_agent(
            name="Available Agent",
            capabilities=["process"],
        )
        await registry.activate_agent(agent.id)

        found = await registry.find_available_agent(capability="process")
        assert found is not None
        assert found.name == "Available Agent"

    @pytest.mark.asyncio
    async def test_find_available_agent_none_available(self, session):
        """Test finding available agent when none match criteria."""
        registry = AgentRegistry(session)

        # Create inactive agent
        await registry.register_agent(
            name="Inactive Agent",
            capabilities=["process"],
        )

        found = await registry.find_available_agent(capability="process")
        assert found is None


class TestClaudeAgentExecutor:
    """Tests for ClaudeAgentExecutor."""

    @pytest.mark.asyncio
    async def test_invoke_agent(self, session, mock_anthropic_client):
        """Test invoking a Claude agent."""
        executor = ClaudeAgentExecutor(session)
        executor._client = mock_anthropic_client

        # Create an agent
        registry = AgentRegistry(session)
        agent, _ = await registry.register_agent(
            name="Invoke Test Agent",
            model="claude-sonnet-4-20250514",
            system_prompt="You are helpful.",
        )

        result = await executor.invoke(
            agent=agent,
            prompt="Hello, agent!",
            workflow_id="wf-123",
        )

        assert result["content"] == "Test response"
        assert result["model"] == "claude-sonnet-4-20250514"
        assert "usage" in result

        # Verify API was called
        mock_anthropic_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_agent_with_context(self, session, mock_anthropic_client):
        """Test invoking an agent with additional context."""
        executor = ClaudeAgentExecutor(session)
        executor._client = mock_anthropic_client

        registry = AgentRegistry(session)
        agent, _ = await registry.register_agent(name="Context Agent")

        context = {"user": "test-user", "session": "sess-123"}

        await executor.invoke(
            agent=agent,
            prompt="Process this",
            context=context,
        )

        # Verify context was included in the message
        call_args = mock_anthropic_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        assert "Context:" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_invoke_agent_records_events(self, session, mock_anthropic_client):
        """Test that invocation records ledger events."""
        executor = ClaudeAgentExecutor(session)
        executor._client = mock_anthropic_client

        registry = AgentRegistry(session)
        agent, _ = await registry.register_agent(name="Event Recording Agent")

        await executor.invoke(
            agent=agent,
            prompt="Test prompt",
            workflow_id="wf-events",
        )

        # Check that events were recorded
        from uaef.ledger.events import LedgerEventService
        from uaef.ledger.models import EventType

        event_service = LedgerEventService(session)
        events = await event_service.get_events_by_workflow("wf-events")

        # Should have AGENT_INVOKED and AGENT_RESPONSE events
        event_types = [e.event_type for e in events]
        assert EventType.AGENT_INVOKED.value in event_types
        assert EventType.AGENT_RESPONSE.value in event_types

    @pytest.mark.asyncio
    async def test_invoke_agent_handles_error(self, session, mock_anthropic_client):
        """Test that invocation errors are recorded."""
        executor = ClaudeAgentExecutor(session)
        executor._client = mock_anthropic_client

        # Configure mock to raise error
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        registry = AgentRegistry(session)
        agent, _ = await registry.register_agent(name="Error Agent")

        with pytest.raises(Exception, match="API Error"):
            await executor.invoke(
                agent=agent,
                prompt="This will fail",
                workflow_id="wf-error",
            )

        # Check error event was recorded
        from uaef.ledger.events import LedgerEventService
        from uaef.ledger.models import EventType

        event_service = LedgerEventService(session)
        events = await event_service.get_events_by_workflow("wf-error")

        event_types = [e.event_type for e in events]
        assert EventType.AGENT_ERROR.value in event_types

    @pytest.mark.asyncio
    async def test_invoke_agent_with_tool_calls(self, session, mock_anthropic_client):
        """Test invoking an agent that returns tool calls."""
        executor = ClaudeAgentExecutor(session)
        executor._client = mock_anthropic_client

        # Configure mock to return tool use
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.id = "tool-123"
        tool_use_block.name = "search"
        tool_use_block.input = {"query": "test"}

        mock_response = MagicMock()
        mock_response.content = [tool_use_block]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.stop_reason = "tool_use"

        mock_anthropic_client.messages.create.return_value = mock_response

        registry = AgentRegistry(session)
        agent, _ = await registry.register_agent(name="Tool Agent")

        result = await executor.invoke(
            agent=agent,
            prompt="Search for something",
        )

        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "search"
        assert result["tool_calls"][0]["input"] == {"query": "test"}
