# UAEF Serverless Functions

AWS Lambda handlers for event-driven workflow execution.

## Handlers

### 1. workflow_trigger.py
Triggers workflow executions via API Gateway or EventBridge.

**Triggers:**
- API Gateway HTTP POST
- EventBridge event
- Direct Lambda invocation

**Environment Variables:**
- `UAEF_DB_URL` - PostgreSQL connection string
- `UAEF_AGENT_ANTHROPIC_API_KEY` - Anthropic API key

**Usage:**
```bash
# API Gateway
POST /workflows/trigger
{
  "definition_id": "wf-def-123",
  "input_data": {"key": "value"},
  "name": "My Workflow",
  "initiated_by": "user-123"
}

# EventBridge
{
  "definition_id": "wf-def-123",
  "input_data": {"key": "value"}
}
```

### 2. webhook_receiver.py
Receives webhooks from external systems (GitHub, Stripe, Salesforce, etc.).

**Triggers:**
- API Gateway HTTP POST

**Environment Variables:**
- `UAEF_DB_URL` - PostgreSQL connection string
- `VERIFY_WEBHOOK_SIGNATURE` - Verify webhook signatures (default: true)

**Usage:**
```bash
POST /webhooks
Headers:
  X-Webhook-Source: github
  X-Webhook-Signature: sha256=...

Body: {webhook payload}
```

### 3. scheduled_workflow.py
Runs workflows on a schedule (cron/rate expressions).

**Triggers:**
- EventBridge Scheduler
- CloudWatch Events

**Environment Variables:**
- `UAEF_DB_URL` - PostgreSQL connection string
- `DAILY_REPORT_WORKFLOW_ID` - Workflow for daily reports
- `CLEANUP_WORKFLOW_ID` - Cleanup workflow ID
- `SYNC_WORKFLOW_ID` - Sync workflow ID

**Schedule Examples:**
- `rate(1 hour)` - Every hour
- `rate(1 day)` - Daily
- `cron(0 9 * * ? *)` - Daily at 9am UTC

## Deployment

### AWS Lambda with SAM

1. Create SAM template (`template.yaml`):
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Globals:
  Function:
    Timeout: 300
    MemorySize: 512
    Runtime: python3.11
    Environment:
      Variables:
        UAEF_DB_URL: !Sub '{{resolve:secretsmanager:uaef-db-url}}'
        UAEF_AGENT_ANTHROPIC_API_KEY: !Sub '{{resolve:secretsmanager:anthropic-api-key}}'
        POWERTOOLS_SERVICE_NAME: uaef
        LOG_LEVEL: INFO

Resources:
  WorkflowTriggerFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: workflow_trigger.handler
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /workflows/trigger
            Method: post

  WebhookReceiverFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: webhook_receiver.handler
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /webhooks
            Method: post

  ScheduledWorkflowFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: scheduled_workflow.handler
      Events:
        DailySchedule:
          Type: Schedule
          Properties:
            Schedule: rate(1 day)
            Input: |
              {
                "schedule_name": "daily-report",
                "definition_id": "wf-def-123"
              }
```

2. Build and deploy:
```bash
# Build
sam build

# Deploy
sam deploy --guided
```

### Manual Lambda Deployment

1. Create deployment package:
```bash
cd functions
pip install -r requirements.txt -t package/
pip install .. -t package/
cd package
zip -r ../deployment.zip .
cd ..
zip -g deployment.zip *.py
```

2. Upload to Lambda:
```bash
aws lambda create-function \
  --function-name uaef-workflow-trigger \
  --runtime python3.11 \
  --handler workflow_trigger.handler \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --zip-file fileb://deployment.zip \
  --timeout 300 \
  --memory-size 512
```

### Azure Functions

For Azure deployment, create `host.json` and `function.json` for each handler.

## Configuration

### Database Connection

Use AWS RDS PostgreSQL or Aurora PostgreSQL for production:

```bash
# Store in Secrets Manager
aws secretsmanager create-secret \
  --name uaef-db-url \
  --secret-string "postgresql://user:pass@rds-endpoint:5432/uaef"
```

### VPC Configuration

If using RDS, configure Lambda functions in the same VPC:

```yaml
VpcConfig:
  SecurityGroupIds:
    - sg-xxxxx
  SubnetIds:
    - subnet-xxxxx
    - subnet-yyyyy
```

### IAM Permissions

Required permissions:
- `secretsmanager:GetSecretValue` - Access database credentials
- `ec2:CreateNetworkInterface` - VPC access (if needed)
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` - CloudWatch Logs

## Monitoring

### CloudWatch Logs

All handlers use AWS Lambda Powertools for structured logging:
```json
{
  "level": "INFO",
  "location": "handler:45",
  "message": "workflow_triggered",
  "timestamp": "2025-01-19T12:00:00.000Z",
  "service": "workflow-trigger",
  "execution_id": "wf-exec-123",
  "definition_id": "wf-def-123"
}
```

### Metrics

Track key metrics:
- Workflow trigger count
- Webhook receipt count
- Scheduled execution count
- Error rates
- Execution duration

### Tracing

X-Ray tracing enabled via Lambda Powertools:
```python
@tracer.capture_lambda_handler
def handler(event, context):
    # Automatically traced
```

## Testing

### Local Testing

```python
# Test workflow trigger
event = {
    "body": json.dumps({
        "definition_id": "test-def",
        "input_data": {"test": True}
    })
}
response = handler(event, None)
```

### Integration Testing

Use AWS SAM CLI:
```bash
# Test locally
sam local invoke WorkflowTriggerFunction -e test_event.json

# Start local API
sam local start-api
curl -X POST http://localhost:3000/workflows/trigger \
  -H "Content-Type: application/json" \
  -d '{"definition_id": "test", "input_data": {}}'
```

## Best Practices

1. **Connection Pooling**: Database connections are reused across invocations
2. **Cold Starts**: Imports inside handler reduce cold start time
3. **Timeouts**: Set appropriate timeout (5-15 minutes for long workflows)
4. **Error Handling**: All errors logged and returned with appropriate status codes
5. **Idempotency**: Use workflow execution IDs to prevent duplicate executions
6. **Secrets**: Never hardcode credentials; use Secrets Manager
7. **Monitoring**: Enable X-Ray and CloudWatch Logs for all functions
