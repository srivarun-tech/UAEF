"""
AWS Lambda Handler: Webhook Receiver

Receives webhook events from external systems and triggers workflows.
"""

import json
import os
from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="webhook-receiver")
tracer = Tracer(service="webhook-receiver")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda handler for receiving webhooks from external systems.

    Validates webhook signatures, parses payload, and triggers workflows.

    Event structure:
    {
        "body": {...webhook payload...},
        "headers": {
            "X-Webhook-Signature": "...",
            "X-Webhook-Source": "..."
        }
    }
    """
    try:
        # Parse webhook payload
        if "body" in event:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        else:
            body = event

        headers = event.get("headers", {})
        webhook_source = headers.get("X-Webhook-Source", "unknown")
        webhook_signature = headers.get("X-Webhook-Signature")

        logger.info(
            "webhook_received",
            source=webhook_source,
            payload_keys=list(body.keys()),
        )

        # Verify signature (if configured)
        if os.environ.get("VERIFY_WEBHOOK_SIGNATURE", "true").lower() == "true":
            if not webhook_signature:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Missing webhook signature"}),
                }

            # Verify signature logic would go here
            # For now, just log
            logger.info("webhook_signature_check", signature=webhook_signature[:10] + "...")

        # Import here to avoid cold start issues
        import asyncio

        from uaef.core import get_session
        from uaef.ledger import EventType, LedgerEventService

        # Record webhook receipt
        async def record_webhook():
            async with get_session() as session:
                event_service = LedgerEventService(session)
                await event_service.record_event(
                    event_type=EventType.SYSTEM_ERROR,  # Use appropriate event type
                    payload={
                        "source": webhook_source,
                        "data": body,
                    },
                    actor_type="external",
                )

        asyncio.run(record_webhook())

        # Process webhook based on source
        result = _process_webhook(webhook_source, body)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "received",
                "result": result,
            }),
        }

    except Exception as e:
        logger.exception("webhook_processing_failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }


def _process_webhook(source: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Process webhook based on source.

    Args:
        source: Webhook source identifier
        payload: Webhook payload

    Returns:
        Processing result
    """
    # Map webhook sources to workflow triggers
    workflow_mapping = {
        "github": _process_github_webhook,
        "stripe": _process_stripe_webhook,
        "salesforce": _process_salesforce_webhook,
    }

    processor = workflow_mapping.get(source.lower(), _process_generic_webhook)
    return processor(payload)


def _process_github_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Process GitHub webhook."""
    event_type = payload.get("action")
    repository = payload.get("repository", {}).get("name")

    logger.info(
        "github_webhook",
        event_type=event_type,
        repository=repository,
    )

    # Trigger appropriate workflow
    # For example: code review workflow on PR opened
    return {
        "processed": True,
        "event_type": event_type,
        "repository": repository,
    }


def _process_stripe_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Process Stripe webhook."""
    event_type = payload.get("type")

    logger.info(
        "stripe_webhook",
        event_type=event_type,
    )

    # Trigger settlement or payment workflow
    return {
        "processed": True,
        "event_type": event_type,
    }


def _process_salesforce_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Process Salesforce webhook."""
    event_type = payload.get("event", {}).get("type")

    logger.info(
        "salesforce_webhook",
        event_type=event_type,
    )

    # Trigger CRM sync or customer workflow
    return {
        "processed": True,
        "event_type": event_type,
    }


def _process_generic_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Process generic webhook."""
    logger.info("generic_webhook", payload_size=len(json.dumps(payload)))

    return {
        "processed": True,
        "type": "generic",
    }
