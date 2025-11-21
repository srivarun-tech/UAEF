"""
AWS Lambda Handler: Scheduled Workflow

Runs workflows on a schedule via EventBridge Scheduler or CloudWatch Events.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="scheduled-workflow")
tracer = Tracer(service="scheduled-workflow")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda handler for scheduled workflow execution.

    Triggered by EventBridge rules on a schedule (cron/rate expressions).

    Event structure:
    {
        "schedule_name": "daily-report",
        "definition_id": "wf-def-123",
        "input_data": {...},
        "metadata": {
            "schedule": "rate(1 day)",
            "last_run": "2025-01-19T00:00:00Z"
        }
    }
    """
    try:
        schedule_name = event.get("schedule_name", "unnamed")
        definition_id = event.get("definition_id")
        input_data = event.get("input_data", {})
        metadata = event.get("metadata", {})

        if not definition_id:
            logger.error("missing_definition_id", schedule=schedule_name)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "definition_id is required"}),
            }

        # Add schedule context to input
        input_data["_schedule"] = {
            "name": schedule_name,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "schedule": metadata.get("schedule"),
            "last_run": metadata.get("last_run"),
        }

        logger.info(
            "scheduled_workflow_triggered",
            schedule=schedule_name,
            definition_id=definition_id,
        )

        # Import here to avoid cold start
        import asyncio

        from uaef.core import get_session
        from uaef.orchestration import WorkflowService

        # Start workflow
        async def start_scheduled_workflow():
            async with get_session() as session:
                service = WorkflowService(session)
                execution = await service.start_workflow(
                    definition_id=definition_id,
                    input_data=input_data,
                    name=f"{schedule_name} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                    initiated_by=schedule_name,
                    initiated_by_type="schedule",
                )
                return execution

        execution = asyncio.run(start_scheduled_workflow())

        logger.info(
            "scheduled_workflow_started",
            schedule=schedule_name,
            execution_id=execution.id,
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "schedule": schedule_name,
                "execution_id": execution.id,
                "status": execution.status,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
            }),
        }

    except Exception as e:
        logger.exception("scheduled_workflow_failed", schedule=event.get("schedule_name"))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }


def get_daily_workflows() -> list[dict[str, Any]]:
    """
    Get list of workflows that should run daily.

    In production, this would query a database or configuration service.

    Returns:
        List of workflow configurations
    """
    return [
        {
            "schedule_name": "daily-report",
            "definition_id": os.environ.get("DAILY_REPORT_WORKFLOW_ID"),
            "input_data": {
                "report_date": datetime.now(timezone.utc).date().isoformat(),
            },
        },
        {
            "schedule_name": "daily-cleanup",
            "definition_id": os.environ.get("CLEANUP_WORKFLOW_ID"),
            "input_data": {
                "retention_days": 30,
            },
        },
    ]


def get_hourly_workflows() -> list[dict[str, Any]]:
    """Get list of workflows that should run hourly."""
    return [
        {
            "schedule_name": "hourly-sync",
            "definition_id": os.environ.get("SYNC_WORKFLOW_ID"),
            "input_data": {
                "sync_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    ]
