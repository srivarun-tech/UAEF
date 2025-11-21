"""
UAEF Message Queue Connectors

Connectors for message queue systems (AWS SQS, Azure Service Bus).
"""

import json
from typing import Any

from uaef.core.logging import get_logger
from uaef.interop.connectors.base import (
    AsyncConnectorMixin,
    BaseConnector,
    ConnectorStatus,
    ConnectorType,
)

logger = get_logger(__name__)


class SQSConnector(BaseConnector, AsyncConnectorMixin):
    """
    AWS SQS (Simple Queue Service) connector.

    Supports sending and receiving messages from SQS queues.
    """

    def __init__(self, connector_id: str, config: dict[str, Any]):
        """
        Initialize SQS connector.

        Config keys:
            - queue_url: SQS queue URL
            - region: AWS region (default: us-east-1)
            - aws_access_key_id: AWS access key (optional, uses IAM if not provided)
            - aws_secret_access_key: AWS secret key (optional)
            - wait_time_seconds: Long polling wait time (default: 10)
            - max_messages: Max messages to receive at once (default: 1)
        """
        super().__init__(connector_id, config)
        self.queue_url = config.get("queue_url")
        self.region = config.get("region", "us-east-1")
        self.wait_time = config.get("wait_time_seconds", 10)
        self.max_messages = config.get("max_messages", 1)
        self.client = None

    async def connect(self) -> None:
        """Initialize SQS client."""
        if self.client is not None:
            return

        self.status = ConnectorStatus.CONNECTING

        try:
            import boto3

            # Create SQS client
            session_config = {"region_name": self.region}

            if self.config.get("aws_access_key_id"):
                session_config["aws_access_key_id"] = self.config["aws_access_key_id"]
                session_config["aws_secret_access_key"] = self.config[
                    "aws_secret_access_key"
                ]

            self.client = boto3.client("sqs", **session_config)

            self.status = ConnectorStatus.CONNECTED
            logger.info(
                "sqs_connected",
                connector_id=self.connector_id,
                queue_url=self.queue_url,
            )

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(
                "sqs_connection_failed",
                connector_id=self.connector_id,
                error=str(e),
            )
            raise ConnectionError(f"Failed to connect to SQS: {e}")

    async def disconnect(self) -> None:
        """Close SQS client."""
        if self.client:
            # boto3 clients don't need explicit cleanup
            self.client = None
            self.status = ConnectorStatus.DISCONNECTED
            logger.info("sqs_disconnected", connector_id=self.connector_id)

    async def send(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """
        Send a message to the SQS queue.

        Args:
            payload: Message payload
            **kwargs: Additional options (MessageAttributes, DelaySeconds)

        Returns:
            SQS response with MessageId
        """
        if not self.client:
            raise ConnectionError("Not connected. Call connect() first.")

        try:
            message_body = json.dumps(payload)

            send_params = {
                "QueueUrl": self.queue_url,
                "MessageBody": message_body,
            }

            # Add optional parameters
            if "MessageAttributes" in kwargs:
                send_params["MessageAttributes"] = kwargs["MessageAttributes"]
            if "DelaySeconds" in kwargs:
                send_params["DelaySeconds"] = kwargs["DelaySeconds"]

            response = self.client.send_message(**send_params)

            logger.info(
                "sqs_message_sent",
                connector_id=self.connector_id,
                message_id=response["MessageId"],
            )

            return {
                "message_id": response["MessageId"],
                "status": "success",
            }

        except Exception as e:
            logger.error(
                "sqs_send_failed",
                connector_id=self.connector_id,
                error=str(e),
            )
            raise

    async def receive(self, **kwargs: Any) -> dict[str, Any] | None:
        """
        Receive messages from the SQS queue.

        Args:
            **kwargs: Additional options (VisibilityTimeout, etc.)

        Returns:
            Message data or None if no messages available
        """
        if not self.client:
            raise ConnectionError("Not connected. Call connect() first.")

        try:
            receive_params = {
                "QueueUrl": self.queue_url,
                "MaxNumberOfMessages": self.max_messages,
                "WaitTimeSeconds": self.wait_time,
                "MessageAttributeNames": ["All"],
            }

            if "VisibilityTimeout" in kwargs:
                receive_params["VisibilityTimeout"] = kwargs["VisibilityTimeout"]

            response = self.client.receive_message(**receive_params)

            messages = response.get("Messages", [])
            if not messages:
                return None

            # Return first message
            message = messages[0]
            body = json.loads(message["Body"])

            logger.info(
                "sqs_message_received",
                connector_id=self.connector_id,
                message_id=message["MessageId"],
            )

            return {
                "message_id": message["MessageId"],
                "receipt_handle": message["ReceiptHandle"],
                "body": body,
                "attributes": message.get("MessageAttributes", {}),
            }

        except Exception as e:
            logger.error(
                "sqs_receive_failed",
                connector_id=self.connector_id,
                error=str(e),
            )
            raise

    async def delete_message(self, receipt_handle: str) -> None:
        """Delete a message from the queue after processing."""
        if not self.client:
            raise ConnectionError("Not connected")

        try:
            self.client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )

            logger.info(
                "sqs_message_deleted",
                connector_id=self.connector_id,
            )

        except Exception as e:
            logger.error(
                "sqs_delete_failed",
                connector_id=self.connector_id,
                error=str(e),
            )
            raise

    async def publish(
        self,
        topic: str,
        message: dict[str, Any],
        **kwargs: Any,
    ) -> str:
        """Publish a message (alias for send)."""
        result = await self.send(message, **kwargs)
        return result["message_id"]

    async def subscribe(
        self,
        topic: str,
        callback: callable,
        **kwargs: Any,
    ) -> None:
        """
        Subscribe to queue with a callback.

        Note: This is a simple implementation. For production,
        consider using AWS Lambda triggers or dedicated worker processes.
        """
        # Simple polling loop
        while True:
            message = await self.receive(**kwargs)
            if message:
                try:
                    await callback(message["body"])
                    await self.delete_message(message["receipt_handle"])
                except Exception as e:
                    logger.error(
                        "sqs_callback_error",
                        connector_id=self.connector_id,
                        error=str(e),
                    )

    def get_connector_type(self) -> ConnectorType:
        """Get connector type."""
        return ConnectorType.MESSAGE_QUEUE


class ServiceBusConnector(BaseConnector, AsyncConnectorMixin):
    """
    Azure Service Bus connector.

    Supports sending and receiving messages from Service Bus queues and topics.
    """

    def __init__(self, connector_id: str, config: dict[str, Any]):
        """
        Initialize Service Bus connector.

        Config keys:
            - connection_string: Service Bus connection string
            - queue_name: Queue name (for queue operations)
            - topic_name: Topic name (for pub/sub operations)
        """
        super().__init__(connector_id, config)
        self.connection_string = config.get("connection_string")
        self.queue_name = config.get("queue_name")
        self.topic_name = config.get("topic_name")
        self.client = None
        self.sender = None
        self.receiver = None

    async def connect(self) -> None:
        """Initialize Service Bus client."""
        if self.client is not None:
            return

        self.status = ConnectorStatus.CONNECTING

        try:
            from azure.servicebus.aio import ServiceBusClient

            self.client = ServiceBusClient.from_connection_string(
                self.connection_string
            )

            # Create sender and receiver based on config
            if self.queue_name:
                self.sender = self.client.get_queue_sender(self.queue_name)
                self.receiver = self.client.get_queue_receiver(self.queue_name)

            self.status = ConnectorStatus.CONNECTED
            logger.info(
                "servicebus_connected",
                connector_id=self.connector_id,
                queue=self.queue_name,
                topic=self.topic_name,
            )

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(
                "servicebus_connection_failed",
                connector_id=self.connector_id,
                error=str(e),
            )
            raise ConnectionError(f"Failed to connect to Service Bus: {e}")

    async def disconnect(self) -> None:
        """Close Service Bus client."""
        if self.sender:
            await self.sender.close()
        if self.receiver:
            await self.receiver.close()
        if self.client:
            await self.client.close()

        self.client = None
        self.sender = None
        self.receiver = None
        self.status = ConnectorStatus.DISCONNECTED
        logger.info("servicebus_disconnected", connector_id=self.connector_id)

    async def send(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Send a message to the queue or topic."""
        if not self.sender:
            raise ConnectionError("Not connected. Call connect() first.")

        try:
            from azure.servicebus import ServiceBusMessage

            message = ServiceBusMessage(json.dumps(payload))

            # Add custom properties
            if "properties" in kwargs:
                for key, value in kwargs["properties"].items():
                    message.application_properties[key] = value

            await self.sender.send_messages(message)

            logger.info(
                "servicebus_message_sent",
                connector_id=self.connector_id,
            )

            return {"status": "success"}

        except Exception as e:
            logger.error(
                "servicebus_send_failed",
                connector_id=self.connector_id,
                error=str(e),
            )
            raise

    async def receive(self, **kwargs: Any) -> dict[str, Any] | None:
        """Receive a message from the queue."""
        if not self.receiver:
            raise ConnectionError("Not connected. Call connect() first.")

        try:
            max_wait_time = kwargs.get("timeout", 10)

            messages = await self.receiver.receive_messages(
                max_wait_time=max_wait_time,
                max_message_count=1,
            )

            if not messages:
                return None

            message = messages[0]
            body = json.loads(str(message))

            logger.info(
                "servicebus_message_received",
                connector_id=self.connector_id,
            )

            return {
                "body": body,
                "properties": message.application_properties,
                "message": message,  # For completing later
            }

        except Exception as e:
            logger.error(
                "servicebus_receive_failed",
                connector_id=self.connector_id,
                error=str(e),
            )
            raise

    async def publish(
        self,
        topic: str,
        message: dict[str, Any],
        **kwargs: Any,
    ) -> str:
        """Publish to a topic."""
        result = await self.send(message, **kwargs)
        return result.get("status", "success")

    async def subscribe(
        self,
        topic: str,
        callback: callable,
        **kwargs: Any,
    ) -> None:
        """Subscribe to messages with a callback."""
        while True:
            message_data = await self.receive(**kwargs)
            if message_data:
                try:
                    await callback(message_data["body"])
                    # Complete the message
                    await self.receiver.complete_message(message_data["message"])
                except Exception as e:
                    logger.error(
                        "servicebus_callback_error",
                        connector_id=self.connector_id,
                        error=str(e),
                    )

    def get_connector_type(self) -> ConnectorType:
        """Get connector type."""
        return ConnectorType.MESSAGE_QUEUE
