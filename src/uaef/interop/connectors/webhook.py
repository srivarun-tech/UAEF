"""
UAEF Webhook Connector

HTTP-based webhook connector for generic integrations.
"""

from typing import Any

import httpx

from uaef.core.logging import get_logger
from uaef.interop.connectors.base import (
    BaseConnector,
    ConnectorStatus,
    ConnectorType,
    SyncConnectorMixin,
)

logger = get_logger(__name__)


class WebhookConnector(BaseConnector, SyncConnectorMixin):
    """
    Webhook connector for HTTP/HTTPS integrations.

    Supports sending data to webhooks and making HTTP requests
    to external APIs.
    """

    def __init__(self, connector_id: str, config: dict[str, Any]):
        """
        Initialize webhook connector.

        Config keys:
            - url: Base URL for the webhook
            - auth: Authentication config (type, token, username, password)
            - headers: Default headers to include
            - timeout: Request timeout in seconds (default: 30)
            - verify_ssl: Whether to verify SSL certificates (default: True)
        """
        super().__init__(connector_id, config)
        self.url = config.get("url")
        self.auth_config = config.get("auth", {})
        self.default_headers = config.get("headers", {})
        self.timeout = config.get("timeout", 30)
        self.verify_ssl = config.get("verify_ssl", True)
        self.client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Establish HTTP client."""
        if self.client is not None:
            return

        self.status = ConnectorStatus.CONNECTING

        # Build auth
        auth = None
        auth_type = self.auth_config.get("type")
        if auth_type == "basic":
            auth = httpx.BasicAuth(
                username=self.auth_config.get("username", ""),
                password=self.auth_config.get("password", ""),
            )
        elif auth_type == "bearer":
            token = self.auth_config.get("token", "")
            self.default_headers["Authorization"] = f"Bearer {token}"

        # Create client
        self.client = httpx.AsyncClient(
            base_url=self.url,
            headers=self.default_headers,
            auth=auth,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

        self.status = ConnectorStatus.CONNECTED
        logger.info("webhook_connected", connector_id=self.connector_id, url=self.url)

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self.status = ConnectorStatus.DISCONNECTED
            logger.info("webhook_disconnected", connector_id=self.connector_id)

    async def send(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """
        Send data via POST request to the webhook.

        Args:
            payload: JSON payload to send
            **kwargs: Additional options (endpoint, method, headers)

        Returns:
            Response data
        """
        if not self.client:
            raise ConnectionError("Not connected. Call connect() first.")

        endpoint = kwargs.get("endpoint", "")
        method = kwargs.get("method", "POST")
        headers = kwargs.get("headers", {})

        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            logger.info(
                "webhook_sent",
                connector_id=self.connector_id,
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
            )

            # Try to parse JSON response
            try:
                return response.json()
            except Exception:
                return {"status": "success", "text": response.text}

        except httpx.HTTPStatusError as e:
            logger.error(
                "webhook_error",
                connector_id=self.connector_id,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise

    async def receive(self, **kwargs: Any) -> dict[str, Any] | None:
        """
        Receive is not applicable for webhook connectors.

        Webhooks are push-based and don't support polling.
        """
        raise NotImplementedError("Webhooks are push-based and don't support receive()")

    async def request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make an HTTP request to the external system.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            payload: Optional request payload
            **kwargs: Additional options (headers, params)

        Returns:
            Response data
        """
        if not self.client:
            raise ConnectionError("Not connected. Call connect() first.")

        headers = kwargs.get("headers", {})
        params = kwargs.get("params")

        try:
            if method.upper() in ["GET", "DELETE"]:
                response = await self.client.request(
                    method=method,
                    url=endpoint,
                    params=params,
                    headers=headers,
                )
            else:
                response = await self.client.request(
                    method=method,
                    url=endpoint,
                    json=payload,
                    params=params,
                    headers=headers,
                )

            response.raise_for_status()

            logger.info(
                "webhook_request",
                connector_id=self.connector_id,
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
            )

            try:
                return response.json()
            except Exception:
                return {"status": "success", "text": response.text}

        except httpx.HTTPStatusError as e:
            logger.error(
                "webhook_request_error",
                connector_id=self.connector_id,
                method=method,
                endpoint=endpoint,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise

    def get_connector_type(self) -> ConnectorType:
        """Get connector type."""
        return ConnectorType.WEBHOOK
