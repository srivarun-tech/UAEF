"""
UAEF Enterprise Connectors

Connectors for integrating with external enterprise systems.
"""

from uaef.interop.connectors.base import (
    AsyncConnectorMixin,
    BaseConnector,
    ConnectorStatus,
    ConnectorType,
    SyncConnectorMixin,
)
from uaef.interop.connectors.erp import OracleERPConnector, SAPConnector
from uaef.interop.connectors.queue import SQSConnector, ServiceBusConnector
from uaef.interop.connectors.webhook import WebhookConnector

__all__ = [
    # Base classes
    "BaseConnector",
    "SyncConnectorMixin",
    "AsyncConnectorMixin",
    "ConnectorStatus",
    "ConnectorType",
    # Webhook
    "WebhookConnector",
    # Message Queues
    "SQSConnector",
    "ServiceBusConnector",
    # ERP
    "SAPConnector",
    "OracleERPConnector",
]
