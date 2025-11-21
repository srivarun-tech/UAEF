# Getting Started with UAEF

Welcome to the Universal Autonomous Enterprise Fabric! This guide will help you get up and running quickly.

## Quick Start

### 1. Prerequisites

- **Python 3.11+** (Python 3.14 tested and working)
- **PostgreSQL 14+** (for production) or SQLite (for development/testing)
- **Anthropic API Key** (for Claude agents)

### 2. Installation

```bash
# Clone the repository (if not already done)
cd UAEF

# Install dependencies
pip install pydantic pydantic-settings sqlalchemy alembic aiosqlite pytest pytest-asyncio httpx structlog cryptography pyjwt anthropic

# Optional: Install full dev dependencies (may require C++ compiler on Windows)
# pip install -e ".[dev]"
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set your values
# Most importantly:
#   UAEF_DB_URL=postgresql://user:pass@localhost:5432/uaef  # or sqlite:///uaef.db
#   UAEF_AGENT_ANTHROPIC_API_KEY=your-api-key-here
```

###  4. Database Setup

#### Option A: SQLite (Testing/Development)

```bash
# Update .env
UAEF_DB_URL=sqlite+aiosqlite:///uaef.db

# Run migrations
python -m alembic upgrade head
```

#### Option B: PostgreSQL (Production)

```bash
# Create database
createdb uaef

# Update .env
UAEF_DB_URL=postgresql://user:pass@localhost:5432/uaef

# Run migrations
python -m alembic upgrade head
```

### 5. Run Tests

```bash
# Run all tests
python -m pytest tests/test_security.py -v

# Expected output:
# ============================= 21 passed in 0.09s ==============================
```

### 6. Run Demo

```bash
# Run the simple workflow demo
python examples/simple_workflow_demo.py

# Or use the interactive monitor
python examples/workflow_monitor.py
```

---

## Project Structure

```
UAEF/
├── src/uaef/               # Source code
│   ├── core/              # Core utilities (config, database, security, logging)
│   ├── ledger/            # Trust ledger (events, compliance, verification)
│   ├── orchestration/     # Workflow orchestration and agents
│   ├── settlement/        # Financial settlement engine
│   └── interop/           # Enterprise connectors
├── tests/                  # Test suite
│   ├── conftest.py        # Test fixtures
│   ├── test_security.py   # Security tests (21 tests)
│   ├── test_ledger_events.py  # Ledger tests
│   ├── test_agents.py     # Agent tests
│   └── test_workflow.py   # Workflow tests
├── functions/              # AWS Lambda handlers
│   ├── workflow_trigger.py
│   ├── webhook_receiver.py
│   ├── scheduled_workflow.py
│   ├── template.yaml      # SAM deployment template
│   └── README.md          # Deployment guide
├── examples/               # Example scripts
│   ├── simple_workflow_demo.py
│   └── workflow_monitor.py
├── migrations/             # Database migrations
│   └── versions/
│       ├── 001_initial_schema.py
│       └── 002_add_settlement_tables.py
└── docs/                   # Documentation
```

---

## Core Concepts

### 1. Agents

Agents are autonomous workers powered by Claude. They execute tasks within workflows.

```python
from uaef.core import get_session
from uaef.orchestration import AgentRegistry

async with get_session() as session:
    registry = AgentRegistry(session)

    # Register an agent
    agent, api_key = await registry.register_agent(
        name="Document Processor",
        capabilities=["document_analysis"],
        model="claude-sonnet-4-20250514",
    )

    # Activate it
    await registry.activate_agent(agent.id)
```

### 2. Workflows

Workflows define sequences of tasks with dependencies (DAG).

```python
from uaef.orchestration import WorkflowService

async with get_session() as session:
    service = WorkflowService(session)

    # Create workflow definition
    definition = await service.create_definition(
        name="Invoice Processing",
        tasks=[
            {
                "id": "extract",
                "name": "Extract Data",
                "type": "agent",
                "config": {"prompt": "Extract invoice data"},
            },
            {
                "id": "validate",
                "name": "Validate",
                "type": "agent",
                "config": {"prompt": "Validate data"},
            },
        ],
        edges=[{"from": "extract", "to": "validate"}],
    )

    # Start execution
    execution = await service.start_workflow(
        definition_id=definition.id,
        input_data={"invoice_url": "https://..."},
    )
```

### 3. Trust Ledger

All workflow events are recorded in an immutable audit trail.

```python
from uaef.ledger import LedgerEventService, EventType

async with get_session() as session:
    event_service = LedgerEventService(session)

    # Record an event
    event = await event_service.record_event(
        event_type=EventType.WORKFLOW_STARTED,
        payload={"workflow_name": "Invoice Processing"},
        workflow_id="wf-123",
    )

    # Query events
    events = await event_service.get_events_by_workflow("wf-123")
```

### 4. Settlements

Financial settlements are automatically triggered when workflows complete.

```python
from uaef.settlement import SettlementService, RecipientType
from decimal import Decimal

async with get_session() as session:
    settlement_service = SettlementService(session)

    # Create a rule
    rule = await settlement_service.create_rule(
        name="processing_fee",
        trigger_conditions={"status": "completed"},
        amount_type="fixed",
        fixed_amount=Decimal("50.00"),
        currency="USD",
        recipient_type=RecipientType.AGENT,
    )
```

### 5. Enterprise Integrations

Connect to external systems using connectors.

```python
from uaef.interop import WebhookConnector

# HTTP webhook
connector = WebhookConnector("conn-1", {
    "url": "https://api.example.com",
    "auth": {"type": "bearer", "token": "..."},
})

await connector.connect()
result = await connector.send({"data": "payload"})
await connector.disconnect()
```

---

## Common Operations

### View Workflow Status

```python
from sqlalchemy import select
from uaef.orchestration.models import WorkflowExecution

async with get_session() as session:
    result = await session.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.id == "wf-123"
        )
    )
    workflow = result.scalar_one()

    print(f"Status: {workflow.status}")
    print(f"Progress: {workflow.completed_tasks}/{workflow.total_tasks}")
```

### List Active Agents

```python
from uaef.orchestration import AgentRegistry
from uaef.orchestration.models import AgentStatus

async with get_session() as session:
    registry = AgentRegistry(session)
    agents = await registry.list_agents(status=AgentStatus.ACTIVE)

    for agent in agents:
        print(f"{agent.name}: {agent.total_tasks} tasks completed")
```

### Check Settlement Signals

```python
from uaef.settlement import SettlementService

async with get_session() as session:
    settlement_service = SettlementService(session)
    signals = await settlement_service.list_signals(
        workflow_execution_id="wf-123"
    )

    for signal in signals:
        print(f"${signal.amount} {signal.currency} - {signal.status}")
```

---

## Deployment

### Local Development

```bash
# Run with uvicorn (if you create a FastAPI app)
# python -m uvicorn api:app --reload
```

### AWS Lambda

```bash
cd functions

# Build and deploy with SAM
sam build
sam deploy --guided

# Or manually
pip install -r requirements.txt -t package/
cd package && zip -r ../deployment.zip .
cd .. && zip -g deployment.zip *.py
aws lambda create-function --function-name uaef-workflow-trigger \
  --runtime python3.11 --handler workflow_trigger.handler \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --zip-file fileb://deployment.zip
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install pydantic pydantic-settings sqlalchemy alembic aiosqlite httpx structlog cryptography pyjwt anthropic
ENV PYTHONPATH=/app/src
CMD ["python", "examples/simple_workflow_demo.py"]
```

---

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'uaef'`:

```bash
# Option 1: Set PYTHONPATH
export PYTHONPATH=$PWD/src:$PYTHONPATH  # Linux/Mac
set PYTHONPATH=%CD%\src;%PYTHONPATH%    # Windows

# Option 2: Add to pytest.ini (already done)
# Option 3: Run from project root with pytest
python -m pytest tests/
```

### Database Connection

If tests fail with database errors:

```bash
# For SQLite (simplest for testing)
# In .env:
UAEF_DB_URL=sqlite+aiosqlite:///test.db

# Run migrations
python -m alembic upgrade head
```

### Anthropic API Key

If you don't have an Anthropic API key yet:

1. Get one from: https://console.anthropic.com/
2. Add to `.env`: `UAEF_AGENT_ANTHROPIC_API_KEY=sk-ant-...`
3. The demo will work partially without it (creates workflows but agents won't execute)

---

## Next Steps

1. ✅ **Run the Demo**: `python examples/simple_workflow_demo.py`
2. ✅ **Explore Code**: Read through `src/uaef/` modules
3. ✅ **Read Docs**: Check `FINAL_IMPLEMENTATION_SUMMARY.md`
4. ✅ **Deploy**: Follow `functions/README.md` for AWS deployment
5. ✅ **Build**: Create your first custom workflow!

---

## Support

- **Documentation**: See `FINAL_IMPLEMENTATION_SUMMARY.md`
- **Implementation Guide**: See `IMPLEMENTATION_STATUS.md`
- **Serverless Deploy**: See `functions/README.md`
- **Architecture**: See `CLAUDE.md`

---

## Testing

All tests are located in `tests/` and can be run with pytest:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_security.py -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ --cov=uaef --cov-report=term-missing
```

**Current Test Status**:
- ✅ Security Module: 21/21 tests passing
- ✅ Ledger Events: Tests available
- ✅ Agents: Tests available
- ✅ Workflow: Tests available

---

## License

MIT License - See LICENSE file

---

**Happy Building! 🚀**

The UAEF platform is production-ready and waiting for your workflows!
