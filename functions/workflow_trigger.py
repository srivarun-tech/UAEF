"""
AWS Lambda Handler: Workflow Trigger

Triggers a workflow execution from an API Gateway or EventBridge event.
"""

import json
import os
from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize Powertools
logger = Logger(service="workflow-trigger")
tracer = Tracer(service="workflow-trigger")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda handler for triggering workflow executions.

    Event structure (API Gateway):
    {
        "body": {
            "definition_id": "wf-def-123",
            "input_data": {...},
            "name": "Optional workflow name",
            "initiated_by": "user-id"
        }
    }

    Event structure (EventBridge):
    {
        "definition_id": "wf-def-123",
        "input_data": {...}
    }
    """
    try:
        # Parse event
        if "body" in event:
            # API Gateway format
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        else:
            # Direct invocation or EventBridge
            body = event

        definition_id = body.get("definition_id")
        input_data = body.get("input_data", {})
        workflow_name = body.get("name")
        initiated_by = body.get("initiated_by")

        if not definition_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "definition_id is required"}),
            }

        # Import here to avoid cold start issues
        import asyncio

        from uaef.core import get_session
        from uaef.agents import WorkflowService

        # Run async workflow start
        async def start_workflow():
            async with get_session() as session:
                service = WorkflowService(session)
                execution = await service.start_workflow(
                    definition_id=definition_id,
                    input_data=input_data,
                    name=workflow_name,
                    initiated_by=initiated_by,
                    initiated_by_type="api" if "body" in event else "event",
                )
                return execution

        execution = asyncio.run(start_workflow())

        logger.info(
            "workflow_triggered",
            execution_id=execution.id,
            definition_id=definition_id,
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "execution_id": execution.id,
                "status": execution.status,
                "workflow_name": execution.name,
            }),
        }

    except ValueError as e:
        logger.error("validation_error", error=str(e))
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)}),
        }

    except Exception as e:
        logger.exception("workflow_trigger_failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }
