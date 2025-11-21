"""
UAEF Platform Adapters

Adapters for integrating agents from different platforms:
- LangChain (via LangServe API)
- AutoGPT (via REST API)
- CrewAI (via REST wrapper)
- Temporal (via Temporal client)
- Custom (generic REST API)
"""

from uaef.agents.adapters.base import AgentAdapter, AdapterError
from uaef.agents.adapters.factory import AdapterFactory

__all__ = [
    "AgentAdapter",
    "AdapterError",
    "AdapterFactory",
]
