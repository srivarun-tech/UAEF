# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UAEF (Universal Autonomous Enterprise Fabric) is an enterprise platform for coordinating autonomous agents, validating workflow integrity through a permissioned trust ledger, and automating financial settlements tied to operational outcomes.

## Common Commands

### Installation
```bash
pip install -e ".[dev]"
```

### Database
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=uaef --cov-report=term-missing

# Run single test file
pytest tests/test_specific.py -v

# Run specific test
pytest tests/test_specific.py::test_function_name -v
```

### Code Quality
```bash
# Format
black src tests

# Lint
ruff check src tests

# Type check
mypy src
```

## Architecture

### Core Components

**Agent Orchestration** (`src/uaef/orchestration/`)
- `AgentRegistry` - Manages agent registration, lifecycle, and authentication
- `ClaudeAgentExecutor` - Invokes Claude agents via Anthropic SDK with ledger event tracking
- Models: `Agent`, `WorkflowDefinition`, `WorkflowExecution`, `TaskExecution`, `Policy`, `HumanApproval`
- Workflow execution uses DAG structure with task dependencies defined in edges

**Trust Ledger** (`src/uaef/ledger/`)
- `LedgerEventService` - Records immutable events with cryptographic hash chain
- `ComplianceService` - Creates and evaluates compliance checkpoints
- `VerificationService` - Verifies chain integrity
- `AuditTrailService` - Query audit history
- Models: `LedgerEvent`, `ComplianceCheckpoint`, `AuditTrail`, `LedgerBlock`

**Core Infrastructure** (`src/uaef/core/`)
- `config.py` - Pydantic settings with `UAEF_` prefix environment variables
- `database.py` - Async SQLAlchemy with `get_session()` context manager
- `security.py` - `TokenManager` (JWT), `EncryptionService`, `HashService`
- `logging.py` - Structured logging with `structlog`

### Key Patterns

**Database Sessions**: Always use async context manager
```python
async with get_session() as session:
    service = LedgerEventService(session)
    # session auto-commits on success, rolls back on exception
```

**Event Recording**: All significant operations logged to trust ledger
```python
await event_service.record_event(
    event_type=EventType.WORKFLOW_STARTED,
    payload={"data": "here"},
    workflow_id="wf-123",
)
```

**Agent Invocation**: Via `ClaudeAgentExecutor` which tracks events automatically
```python
executor = ClaudeAgentExecutor(session)
result = await executor.invoke(agent, prompt, workflow_id=wf_id)
```

### Configuration

Environment variables use `UAEF_` prefix. Key settings:
- `UAEF_ENVIRONMENT` - development/staging/production
- `UAEF_DB_URL` - PostgreSQL connection URL
- `UAEF_AGENT_ANTHROPIC_API_KEY` - Required for Claude agent execution
- `UAEF_SECURITY_JWT_SECRET` - JWT signing secret

### Dependencies

- Python 3.11+
- PostgreSQL 14+
- SQLAlchemy 2.0 (async)
- Pydantic 2.0 for settings/validation
- Anthropic SDK for Claude agents
- FastAPI for API layer

### Status Enums

Workflow states: PENDING → RUNNING → (PAUSED/WAITING_APPROVAL) → COMPLETED/FAILED/CANCELLED
Task states: PENDING → QUEUED → RUNNING → (WAITING_INPUT) → COMPLETED/FAILED/SKIPPED/CANCELLED
Agent states: REGISTERED → ACTIVE ↔ BUSY/PAUSED/ERROR → DEACTIVATED
