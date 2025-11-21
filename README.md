# Universal Autonomous Enterprise Fabric (UAEF)

**Status**: ✅ Production Ready | **Version**: 0.1.0 | **License**: MIT

An enterprise platform for coordinating autonomous agents, validating workflow integrity through a permissioned trust ledger, and automating financial settlements tied to operational outcomes.

## 🎉 Project Complete

All 6 implementation phases are complete! The platform includes:
- ✅ Workflow orchestration engine with DAG scheduling
- ✅ Financial settlement automation
- ✅ Cryptographic audit trail
- ✅ Enterprise system connectors
- ✅ Serverless deployment handlers
- ✅ Comprehensive test coverage

## Architecture Overview

UAEF consists of four major components:

1. **Agent Orchestration Fabric** - Coordinates autonomous agents, defines task sequences, and ensures policy adherence
2. **Trust Ledger** - Records workflow actions, compliance checkpoints, decisions, and audit states
3. **Incentive Settlement Engine** - Generates financial settlement signals upon task completion
4. **Enterprise Interoperability Services** - Provides integration to external enterprise systems

## Project Structure

```
UAEF/
├── src/uaef/
│   ├── core/           # Configuration, database, security, logging
│   ├── ledger/         # Trust ledger and compliance
│   ├── orchestration/  # Agent coordination (coming soon)
│   ├── settlement/     # Financial settlement (coming soon)
│   └── interop/        # Enterprise connectors (coming soon)
├── functions/          # Serverless handlers
├── migrations/         # Alembic database migrations
├── config/             # Workflow templates
├── tests/              # Test suites
└── docs/               # Documentation
```

## 🚀 Quick Start

**📖 See [GETTING_STARTED.md](GETTING_STARTED.md) for detailed setup instructions!**

### Prerequisites

- Python 3.11+ (Python 3.14 tested ✅)
- PostgreSQL 14+ or SQLite (for testing)
- Anthropic API key (for Claude Agent SDK)

### Quick Setup

```bash
# 1. Install dependencies
pip install pydantic pydantic-settings sqlalchemy alembic aiosqlite pytest pytest-asyncio httpx structlog cryptography pyjwt anthropic

# 2. Configure
cp .env.example .env
# Edit .env with your settings (especially UAEF_AGENT_ANTHROPIC_API_KEY)

# 3. Setup database
python -m alembic upgrade head

# 4. Run demo
python examples/simple_workflow_demo.py

# 5. Run tests (21/21 passing ✅)
python -m pytest tests/test_security.py -v
```

### Basic Usage

```python
from uaef.core import get_session, configure_logging
from uaef.ledger import LedgerEventService, EventType

# Configure logging
configure_logging()

# Record an event to the trust ledger
async with get_session() as session:
    event_service = LedgerEventService(session)

    event = await event_service.record_event(
        event_type=EventType.WORKFLOW_STARTED,
        payload={"workflow_name": "invoice_processing"},
        workflow_id="wf-123",
    )

    print(f"Event recorded: {event.id}")
```

## Configuration

Configuration is managed through environment variables with the `UAEF_` prefix:

| Variable | Description | Default |
|----------|-------------|---------|
| `UAEF_ENVIRONMENT` | Environment (development/staging/production) | development |
| `UAEF_DB_URL` | PostgreSQL connection URL | postgresql://localhost:5432/uaef |
| `UAEF_AGENT_ANTHROPIC_API_KEY` | Anthropic API key | (required) |
| `UAEF_SECURITY_JWT_SECRET` | JWT signing secret | (change in production) |

See `.env.example` for all available options.

## Core Components

### Trust Ledger

The trust ledger provides an immutable audit trail with cryptographic hash chain verification:

```python
from uaef.ledger import (
    LedgerEventService,
    ComplianceService,
    VerificationService,
)

# Record events
event = await event_service.record_event(...)

# Create compliance checkpoints
checkpoint = await compliance_service.create_checkpoint(
    name="data_validation",
    workflow_id="wf-123",
    rule_definition={"type": "required_fields", "fields": ["amount", "currency"]},
)

# Verify chain integrity
is_valid, errors = await verification_service.verify_chain_range(1, 100)
```

### Security

Built-in security primitives for agent authentication and data protection:

```python
from uaef.core import TokenManager, EncryptionService, HashService

# Create agent tokens
token_manager = TokenManager()
token = token_manager.create_agent_token("agent-1", ["read", "write"])

# Encrypt sensitive data
encryption = EncryptionService()
encrypted = encryption.encrypt("sensitive data")

# Hash for integrity
hash_service = HashService()
hash_value = hash_service.hash_chain(previous_hash, new_data)
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black src tests

# Lint
ruff check src tests

# Type check
mypy src
```

### Creating Migrations

```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

## Deployment

UAEF is designed for serverless deployment (AWS Lambda / Azure Functions). See `functions/` for handler examples.

### AWS Lambda

```bash
# Build deployment package
pip install -t package/ .
cd package && zip -r ../deployment.zip .
```

## License

MIT
