"""
Adapter Factory

Factory for creating platform-specific agent adapters.
"""

from typing import Dict, Optional, Type

from uaef.agents.adapters.base import AgentAdapter, AdapterError
from uaef.agents.models import AgentPlatform


class UnsupportedPlatformError(AdapterError):
    """Raised when platform is not supported."""
    pass


class AdapterFactory:
    """
    Factory for creating platform-specific adapters.

    Maps AgentPlatform enums to their corresponding adapter implementations.
    """

    _adapters: Dict[AgentPlatform, Type[AgentAdapter]] = {}

    @classmethod
    def register_adapter(
        cls,
        platform: AgentPlatform,
        adapter_class: Type[AgentAdapter],
    ):
        """
        Register an adapter for a platform.

        Args:
            platform: Platform type
            adapter_class: Adapter class to register
        """
        cls._adapters[platform] = adapter_class

    @classmethod
    def get_adapter(
        cls,
        platform: AgentPlatform,
        config: Optional[Dict] = None,
    ) -> AgentAdapter:
        """
        Get adapter instance for a platform.

        Args:
            platform: Platform type
            config: Optional platform-specific configuration

        Returns:
            Adapter instance

        Raises:
            UnsupportedPlatformError: If platform not supported
        """
        adapter_class = cls._adapters.get(platform)

        if not adapter_class:
            raise UnsupportedPlatformError(
                f"No adapter registered for platform: {platform}. "
                f"Supported platforms: {list(cls._adapters.keys())}"
            )

        return adapter_class(config=config)

    @classmethod
    def get_supported_platforms(cls) -> list[AgentPlatform]:
        """Get list of supported platforms."""
        return list(cls._adapters.keys())

    @classmethod
    def is_platform_supported(cls, platform: AgentPlatform) -> bool:
        """Check if a platform is supported."""
        return platform in cls._adapters


# Register available adapters
from uaef.agents.adapters.claude import ClaudeAdapter

AdapterFactory.register_adapter(AgentPlatform.CLAUDE, ClaudeAdapter)

# Future adapters will be registered here as they're implemented:
# from uaef.agents.adapters.langchain import LangChainAdapter
# from uaef.agents.adapters.autogpt import AutoGPTAdapter
# from uaef.agents.adapters.crewai import CrewAIAdapter
#
# AdapterFactory.register_adapter(AgentPlatform.LANGCHAIN, LangChainAdapter)
# AdapterFactory.register_adapter(AgentPlatform.AUTOGPT, AutoGPTAdapter)
# AdapterFactory.register_adapter(AgentPlatform.CREWAI, CrewAIAdapter)
