"""
UAEF Agent Registry Service

Manages agent lifecycle, registration, and invocation
with Claude Agent SDK integration.
"""

from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uaef.core.config import get_settings
from uaef.core.logging import get_logger
from uaef.core.security import HashService, generate_api_key
from uaef.ledger import EventType, LedgerEventService
from uaef.agents.models import Agent, AgentStatus

logger = get_logger(__name__)


class AgentRegistry:
    """Service for managing agent registration and lifecycle."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.hash_service = HashService()
        self.event_service = LedgerEventService(session)

    async def register_agent(
        self,
        name: str,
        agent_type: str = "claude",
        description: str | None = None,
        capabilities: list[str] | None = None,
        configuration: dict[str, Any] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> tuple[Agent, str]:
        """
        Register a new agent.

        Returns:
            Tuple of (agent, api_key)
        """
        settings = get_settings()

        # Generate API key for agent authentication
        api_key = generate_api_key()
        api_key_hash = self.hash_service.hash(api_key)

        # Create agent
        agent = Agent(
            name=name,
            description=description,
            agent_type=agent_type,
            capabilities=capabilities or [],
            configuration=configuration or {},
            model=model or settings.agent.default_model,
            system_prompt=system_prompt,
            tools=tools or [],
            api_key_hash=api_key_hash,
            status=AgentStatus.REGISTERED,
        )

        self.session.add(agent)
        await self.session.flush()

        # Record registration in ledger
        await self.event_service.record_event(
            event_type=EventType.AGENT_REGISTERED,
            payload={
                "agent_name": name,
                "agent_type": agent_type,
                "capabilities": capabilities or [],
            },
            agent_id=agent.id,
        )

        logger.info(
            "agent_registered",
            agent_id=agent.id,
            name=name,
            agent_type=agent_type,
        )

        return agent, api_key

    async def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_agent_by_name(self, name: str) -> Agent | None:
        """Get an agent by name."""
        result = await self.session.execute(
            select(Agent).where(Agent.name == name)
        )
        return result.scalar_one_or_none()

    async def list_agents(
        self,
        status: AgentStatus | None = None,
        agent_type: str | None = None,
        capability: str | None = None,
    ) -> list[Agent]:
        """List agents with optional filters."""
        query = select(Agent)

        if status:
            query = query.where(Agent.status == status)
        if agent_type:
            query = query.where(Agent.agent_type == agent_type)

        result = await self.session.execute(query.order_by(Agent.name))
        agents = list(result.scalars().all())

        # Filter by capability if specified
        if capability:
            agents = [a for a in agents if capability in a.capabilities]

        return agents

    async def activate_agent(self, agent_id: str) -> Agent:
        """Activate an agent for task execution."""
        agent = await self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        agent.status = AgentStatus.ACTIVE
        await self.session.flush()

        logger.info("agent_activated", agent_id=agent_id)
        return agent

    async def deactivate_agent(self, agent_id: str) -> Agent:
        """Deactivate an agent."""
        agent = await self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        agent.status = AgentStatus.DEACTIVATED
        await self.session.flush()

        logger.info("agent_deactivated", agent_id=agent_id)
        return agent

    async def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
    ) -> Agent:
        """Update agent status."""
        agent = await self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        agent.status = status
        await self.session.flush()
        return agent

    async def update_agent_metrics(
        self,
        agent_id: str,
        success: bool,
    ) -> None:
        """Update agent task metrics."""
        agent = await self.get_agent(agent_id)
        if agent:
            agent.total_tasks += 1
            if success:
                agent.successful_tasks += 1
            else:
                agent.failed_tasks += 1
            await self.session.flush()

    async def verify_agent_key(self, agent_id: str, api_key: str) -> bool:
        """Verify an agent's API key."""
        agent = await self.get_agent(agent_id)
        if not agent or not agent.api_key_hash:
            return False

        key_hash = self.hash_service.hash(api_key)
        return key_hash == agent.api_key_hash

    async def find_available_agent(
        self,
        capability: str | None = None,
        agent_type: str = "claude",
    ) -> Agent | None:
        """Find an available agent matching criteria."""
        agents = await self.list_agents(
            status=AgentStatus.ACTIVE,
            agent_type=agent_type,
            capability=capability,
        )
        return agents[0] if agents else None


class ClaudeAgentExecutor:
    """Executor for Claude-based agents using the Anthropic SDK."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.event_service = LedgerEventService(session)
        self._client: anthropic.Anthropic | None = None

    @property
    def client(self) -> anthropic.Anthropic:
        """Get or create Anthropic client."""
        if self._client is None:
            api_key = self.settings.agent.anthropic_api_key.get_secret_value()
            if not api_key:
                raise ValueError("Anthropic API key not configured")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    async def invoke(
        self,
        agent: Agent,
        prompt: str,
        context: dict[str, Any] | None = None,
        workflow_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Invoke a Claude agent with a prompt.

        Returns:
            Dict with response content and metadata
        """
        # Record invocation in ledger
        await self.event_service.record_event(
            event_type=EventType.AGENT_INVOKED,
            payload={
                "agent_name": agent.name,
                "model": agent.model,
                "prompt_length": len(prompt),
            },
            workflow_id=workflow_id,
            task_id=task_id,
            agent_id=agent.id,
        )

        try:
            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Add context if provided
            if context:
                context_str = "\n".join(
                    f"{k}: {v}" for k, v in context.items()
                )
                messages[0]["content"] = f"Context:\n{context_str}\n\nTask:\n{prompt}"

            # Call Claude API
            api_params = {
                "model": agent.model or self.settings.agent.default_model,
                "max_tokens": 4096,
                "system": agent.system_prompt or "You are a helpful assistant.",
                "messages": messages,
            }

            # Only include tools if they exist
            if agent.tools:
                api_params["tools"] = agent.tools

            response = self.client.messages.create(**api_params)

            # Extract response content
            content = ""
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            result = {
                "content": content,
                "tool_calls": tool_calls,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                "stop_reason": response.stop_reason,
            }

            # Record response in ledger
            await self.event_service.record_event(
                event_type=EventType.AGENT_RESPONSE,
                payload={
                    "agent_name": agent.name,
                    "response_length": len(content),
                    "tool_calls": len(tool_calls),
                    "usage": result["usage"],
                },
                workflow_id=workflow_id,
                task_id=task_id,
                agent_id=agent.id,
            )

            logger.info(
                "agent_invoked",
                agent_id=agent.id,
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            return result

        except Exception as e:
            # Record error in ledger
            await self.event_service.record_event(
                event_type=EventType.AGENT_ERROR,
                payload={
                    "agent_name": agent.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                workflow_id=workflow_id,
                task_id=task_id,
                agent_id=agent.id,
            )

            logger.error(
                "agent_error",
                agent_id=agent.id,
                error=str(e),
            )
            raise

    async def invoke_with_tools(
        self,
        agent: Agent,
        prompt: str,
        tools: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
        workflow_id: str | None = None,
        task_id: str | None = None,
        max_iterations: int = 10,
    ) -> dict[str, Any]:
        """
        Invoke agent with tools in an agentic loop.

        Continues until the agent stops using tools or max iterations reached.
        """
        messages = [{"role": "user", "content": prompt}]
        all_tool_calls = []

        for iteration in range(max_iterations):
            response = self.client.messages.create(
                model=agent.model or self.settings.agent.default_model,
                max_tokens=4096,
                system=agent.system_prompt or "You are a helpful assistant.",
                messages=messages,
                tools=tools,
            )

            # Check if we should continue
            if response.stop_reason == "end_turn":
                # Extract final content
                content = ""
                for block in response.content:
                    if block.type == "text":
                        content += block.text

                return {
                    "content": content,
                    "tool_calls": all_tool_calls,
                    "iterations": iteration + 1,
                    "model": response.model,
                }

            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_call = {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                    all_tool_calls.append(tool_call)

                    # Tool execution would happen here
                    # For now, return a placeholder
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Tool execution not implemented",
                    })

            # Add assistant response and tool results to messages
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        return {
            "content": "Max iterations reached",
            "tool_calls": all_tool_calls,
            "iterations": max_iterations,
            "model": agent.model,
        }
