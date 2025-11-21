"""
Claude Adapter

Adapter for Claude agents via Anthropic API.
Integrates with existing ClaudeAgentExecutor.
"""

import httpx
from typing import Any, Dict, Optional

from uaef.agents.adapters.base import AgentAdapter, AgentInvocationError


class ClaudeAdapter(AgentAdapter):
    """
    Adapter for Claude agents via Anthropic API.

    Uses the Anthropic API directly to invoke Claude models.
    """

    async def invoke(
        self,
        agent_id: str,
        endpoint_url: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke a Claude agent.

        For Claude agents, endpoint_url is optional since we use the Anthropic API directly.

        Args:
            agent_id: UAEF agent ID
            endpoint_url: Not used for Claude (uses Anthropic API)
            input_data: Input containing 'prompt' and optional 'system'
            context: Optional context with model, max_tokens, etc.

        Returns:
            Dict with 'content' containing Claude's response

        Raises:
            AgentInvocationError: If invocation fails
        """
        try:
            # Extract configuration
            prompt = input_data.get("prompt", "")
            system = input_data.get("system")

            config = context or {}
            model = config.get("model", "claude-sonnet-4-20250514")
            max_tokens = config.get("max_tokens", 1024)

            # For now, return a placeholder response
            # In Phase 1, this will integrate with the actual Anthropic API
            # via the existing ClaudeAgentExecutor

            return {
                "content": f"[Claude Adapter: Would invoke with prompt='{prompt[:50]}...']",
                "model": model,
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
                "stop_reason": "end_turn",
            }

        except Exception as e:
            raise AgentInvocationError(f"Claude invocation failed: {str(e)}")

    async def validate_agent(
        self,
        agent_id: str,
        endpoint_url: str,
    ) -> bool:
        """
        Validate Claude agent (always returns True for MVP).

        Args:
            agent_id: UAEF agent ID
            endpoint_url: Not used for Claude

        Returns:
            True if agent is valid
        """
        # For Claude agents, validation is simple - just check API key exists
        # In production, this would verify the API key with Anthropic
        return True

    async def get_agent_metadata(
        self,
        agent_id: str,
        endpoint_url: str,
    ) -> Dict[str, Any]:
        """
        Get Claude agent metadata.

        Returns:
            Dict with Claude-specific metadata
        """
        return {
            "platform": "claude",
            "provider": "anthropic",
            "supported_models": [
                "claude-sonnet-4-20250514",
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
            ],
            "capabilities": [
                "text-generation",
                "analysis",
                "code-generation",
                "tool-use",
            ],
        }
