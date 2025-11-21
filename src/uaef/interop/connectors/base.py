"""
UAEF Base Connector

Abstract base class for enterprise system connectors.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ConnectorStatus(str, Enum):
    """Status of a connector."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class ConnectorType(str, Enum):
    """Types of connectors."""

    WEBHOOK = "webhook"
    MESSAGE_QUEUE = "message_queue"
    ERP = "erp"
    DATABASE = "database"
    API = "api"
    CUSTOM = "custom"


class BaseConnector(ABC):
    """
    Abstract base class for all connectors.

    Connectors provide integration with external enterprise systems.
    """

    def __init__(self, connector_id: str, config: dict[str, Any]):
        """
        Initialize connector.

        Args:
            connector_id: Unique identifier for this connector instance
            config: Configuration dictionary for the connector
        """
        self.connector_id = connector_id
        self.config = config
        self.status = ConnectorStatus.DISCONNECTED

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the external system.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the external system."""
        pass

    @abstractmethod
    async def send(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """
        Send data to the external system.

        Args:
            payload: Data to send
            **kwargs: Additional connector-specific parameters

        Returns:
            Response from the external system

        Raises:
            ConnectionError: If not connected
            ValueError: If payload is invalid
        """
        pass

    @abstractmethod
    async def receive(self, **kwargs: Any) -> dict[str, Any] | None:
        """
        Receive data from the external system.

        Args:
            **kwargs: Connector-specific parameters (timeout, filters, etc.)

        Returns:
            Received data, or None if no data available

        Raises:
            ConnectionError: If not connected
        """
        pass

    async def test_connection(self) -> bool:
        """
        Test if the connection is working.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            await self.connect()
            await self.disconnect()
            return True
        except Exception:
            return False

    def get_status(self) -> ConnectorStatus:
        """Get current connector status."""
        return self.status

    @abstractmethod
    def get_connector_type(self) -> ConnectorType:
        """Get the type of this connector."""
        pass


class SyncConnectorMixin:
    """
    Mixin for connectors that support synchronous request/response.

    Use for HTTP APIs, databases, etc.
    """

    @abstractmethod
    async def request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make a synchronous request to the external system.

        Args:
            method: Request method (GET, POST, etc.)
            endpoint: Endpoint or path
            payload: Optional request payload
            **kwargs: Additional parameters

        Returns:
            Response from the system
        """
        pass


class AsyncConnectorMixin:
    """
    Mixin for connectors that support asynchronous messaging.

    Use for message queues, event streams, etc.
    """

    @abstractmethod
    async def publish(
        self,
        topic: str,
        message: dict[str, Any],
        **kwargs: Any,
    ) -> str:
        """
        Publish a message to a topic/queue.

        Args:
            topic: Topic or queue name
            message: Message payload
            **kwargs: Additional parameters

        Returns:
            Message ID or confirmation
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        topic: str,
        callback: callable,
        **kwargs: Any,
    ) -> None:
        """
        Subscribe to a topic/queue.

        Args:
            topic: Topic or queue name
            callback: Function to call when messages arrive
            **kwargs: Additional parameters
        """
        pass
