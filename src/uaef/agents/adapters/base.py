"""
Base Adapter Interface

Abstract base class for platform-specific agent adapters.
All adapters must implement this interface to ensure consistent behavior.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AdapterError(Exception):
    """Base exception for adapter errors."""
    pass


class AgentInvocationError(AdapterError):
    """Raised when agent invocation fails."""
    pass


class AgentValidationError(AdapterError):
    """Raised when agent validation fails."""
    pass


class AgentAdapter(ABC):
    """
    Base adapter for platform-specific agent integration.

    Each platform (LangChain, AutoGPT, CrewAI, Temporal) implements this
    interface to provide a unified way to invoke agents on their native platforms.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize adapter with optional configuration.

        Args:
            config: Platform-specific configuration (API keys, endpoints, etc.)
        """
        self.config = config or {}

    @abstractmethod
    async def invoke(
        self,
        agent_id: str,
        endpoint_url: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke an agent and return results.

        Args:
            agent_id: UAEF agent ID
            endpoint_url: Platform-specific endpoint URL for the agent
            input_data: Input data to pass to the agent
            context: Optional context/configuration for execution

        Returns:
            Dict containing agent output and metadata

        Raises:
            AgentInvocationError: If invocation fails
        """
        pass

    @abstractmethod
    async def validate_agent(
        self,
        agent_id: str,
        endpoint_url: str,
    ) -> bool:
        """
        Verify that an agent exists and is accessible.

        Args:
            agent_id: UAEF agent ID
            endpoint_url: Platform-specific endpoint URL

        Returns:
            True if agent is valid and accessible

        Raises:
            AgentValidationError: If validation fails
        """
        pass

    async def get_agent_metadata(
        self,
        agent_id: str,
        endpoint_url: str,
    ) -> Dict[str, Any]:
        """
        Retrieve agent capabilities and metadata (optional).

        Args:
            agent_id: UAEF agent ID
            endpoint_url: Platform-specific endpoint URL

        Returns:
            Dict containing agent metadata (capabilities, version, etc.)
        """
        return {}

    async def health_check(self) -> bool:
        """
        Check if the adapter and platform are healthy (optional).

        Returns:
            True if adapter can connect to platform
        """
        return True
