# Universal Autonomous Enterprise Fabric (UAEF)

**Status**: 🚧 Active Development | **Version**: 0.2.0 | **License**: MIT

A **platform-agnostic agent integration fabric** that connects autonomous agents across different platforms (LangChain, AutoGPT, CrewAI, Temporal) with verifiable reputation tracking, cryptographic audit trails, and marketplace infrastructure.

## 🎯 Vision

**UAEF is the Switzerland of agent platforms**: neutral, trusted, and universally compatible.

Instead of building another workflow orchestration engine (competing with Temporal/Prefect/Airflow), UAEF provides:

1. **Cross-Platform Agent Integration** - Connect agents from any platform (LangChain, AutoGPT, CrewAI, Temporal, custom)
2. **Verifiable Reputation System** - Track agent performance, success rates, and reliability with immutable proof
3. **Agent Marketplace** - Discover, evaluate, and execute agents based on capabilities and trust scores
4. **Universal Trust Layer** - Cryptographic audit trail for every agent execution across all platforms

## Why UAEF?

| Challenge | UAEF Solution |
|-----------|---------------|
| Agents locked to specific platforms | Platform-agnostic adapters |
| No visibility into agent quality | Reputation scoring with verifiable metrics |
| Trust and transparency issues | Immutable ledger with cryptographic verification |
| Fragmented agent ecosystem | Unified marketplace and discovery |
| Complex integration | Simple REST API + SDKs |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    UAEF Platform Layer                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Agent      │  │  Reputation  │  │  Marketplace │     │
│  │  Registry    │  │   Engine     │  │  & Discovery │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Universal Agent Adapter Framework            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│  │LangChain│ │ AutoGPT │ │ CrewAI  │ │ Temporal│  ...    │
│  │ Adapter │ │ Adapter │ │ Adapter │ │ Adapter │         │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Trust Ledger (✓ Implemented)            │  │
│  │     • Immutable event log                            │  │
│  │     • Cryptographic hash chains                      │  │
│  │     • Compliance checkpoints                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Security Layer (✓ Implemented)             │  │
│  │     • JWT authentication                             │  │
│  │     • Encryption                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │LangChain│         │ AutoGPT │         │ CrewAI  │
   │ Agents  │         │ Agents  │         │ Agents  │
   └─────────┘         └─────────┘         └─────────┘
   (Native Platform)   (Native Platform)   (Native Platform)
```

**Key Principles:**
1. **Platform Agnostic** - Agents execute on their native platforms
2. **Trust Layer** - Every invocation recorded in immutable ledger
3. **Marketplace** - Central discovery and selection with reputation
4. **Adapters** - Translate between UAEF API and platform-specific APIs

## 🏗️ Current Implementation Status

### ✅ Completed (Production Ready)
- **Trust Ledger** - Immutable audit trail with cryptographic hash chains
- **Security Layer** - JWT authentication, encryption, hash chain verification
- **Database Infrastructure** - SQLAlchemy ORM with Alembic migrations
- **Testing Framework** - 77/77 tests passing
- **Pilot Cockpit** - Web-based monitoring dashboard

### 🚧 In Development (Phase 0 Refactoring)
- **Agent Platform Models** - Multi-platform agent support
- **Adapter Framework** - Base interface for platform adapters
- **Agent Registry** - Registration and discovery service
- **Reputation Engine** - Performance tracking and trust scores

### 📋 Planned (Next Phases)
- **Platform Adapters** - LangChain, AutoGPT, CrewAI, Temporal
- **Marketplace API** - Agent discovery and transactions
- **Developer SDKs** - Python, TypeScript, CLI
- **Enterprise Features** - Multi-tenancy, private agents, governance

## Project Structure

```
UAEF/
├── src/uaef/
│   ├── core/           # Configuration, database, security, logging
│   ├── ledger/         # Trust ledger and compliance ✅
│   ├── agents/         # Agent integration fabric (renamed from orchestration) 🚧
│   │   ├── models.py       # Agent, Execution, Reputation models
│   │   ├── registry.py     # Agent registration and discovery
│   │   ├── execution.py    # Cross-platform agent execution
│   │   ├── reputation.py   # Performance tracking and scoring
│   │   └── adapters/       # Platform-specific adapters
│   │       ├── base.py         # AgentAdapter interface
│   │       ├── factory.py      # Adapter factory
│   │       ├── langchain.py    # LangChain integration
│   │       ├── autogpt.py      # AutoGPT integration
│   │       ├── crewai.py       # CrewAI integration
│   │       └── temporal.py     # Temporal integration
│   ├── settlement/     # Transaction tracking and settlements ✅
│   └── interop/        # Enterprise connectors (future)
├── cockpit/            # Web-based monitoring dashboard ✅
├── functions/          # Serverless handlers
├── migrations/         # Alembic database migrations
├── examples/           # Usage examples and demos
├── tests/              # Test suites
└── docs/               # Documentation
```

## 🚀 Quick Start

**📖 See [GETTING_STARTED.md](GETTING_STARTED.md) for detailed setup instructions!**

### Prerequisites

- Python 3.11+ (Python 3.14 tested ✅)
- PostgreSQL 14+ or SQLite (for testing)
- Anthropic API key (for agent execution)

### Installation

```bash
# 1. Install dependencies
pip install pydantic pydantic-settings sqlalchemy alembic aiosqlite pytest pytest-asyncio httpx structlog cryptography pyjwt anthropic fastapi uvicorn

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings (especially UAEF_AGENT_ANTHROPIC_API_KEY)

# 3. Setup database
python -m alembic upgrade head

# 4. Run demo
python run_demo.py

# 5. Start Pilot Cockpit (monitoring dashboard)
python cockpit/api.py
# Open http://localhost:8080
```

### Quick Example

```python
from uaef.core import get_session, configure_logging
from uaef.agents import AgentRegistryService, AgentExecutionService
from uaef.agents.models import AgentPlatform

configure_logging()

async with get_session() as session:
    registry = AgentRegistryService(session)

    # Register an agent from any platform
    agent = await registry.register_agent(
        name="My LangChain Agent",
        platform=AgentPlatform.LANGCHAIN,
        endpoint_url="https://my-agent.com/invoke",
        capabilities=["text-generation", "web-search"],
        metadata={"model": "gpt-4"}
    )

    # Execute agent (cross-platform)
    executor = AgentExecutionService(session)
    result = await executor.execute_agent(
        agent_id=agent.id,
        input_data={"query": "What are the latest AI trends?"}
    )

    # All executions are tracked in immutable ledger
    # Reputation automatically updated
    print(f"Result: {result.output}")
    print(f"Trust Score: {agent.reputation.trust_score}")
```

## Core Features

### 1. Platform-Agnostic Agent Integration

Connect agents from any platform:

```python
# LangChain agent
langchain_agent = await registry.register_agent(
    platform=AgentPlatform.LANGCHAIN,
    endpoint_url="https://langserve.com/my-agent/invoke"
)

# AutoGPT agent
autogpt_agent = await registry.register_agent(
    platform=AgentPlatform.AUTOGPT,
    endpoint_url="https://autogpt.com/api/agents/123"
)

# Execute any agent the same way
result = await executor.execute_agent(langchain_agent.id, input_data)
```

### 2. Verifiable Reputation System

Every execution updates agent reputation with verifiable metrics:

```python
from uaef.agents import ReputationService

reputation_service = ReputationService(session)

# Get agent reputation
reputation = await reputation_service.get_reputation(agent_id)
print(f"Trust Score: {reputation.trust_score}")  # 0-100
print(f"Success Rate: {reputation.success_rate}")
print(f"Avg Latency: {reputation.avg_latency_ms}ms")
print(f"Total Executions: {reputation.total_executions}")

# Get leaderboard
top_agents = await reputation_service.get_leaderboard(limit=10)
```

### 3. Immutable Trust Ledger

Every agent execution is cryptographically recorded:

```python
from uaef.ledger import LedgerEventService, VerificationService

# All executions automatically recorded
ledger = LedgerEventService(session)
events = await ledger.get_events_by_agent(agent_id)

# Verify chain integrity
verification = VerificationService(session)
is_valid, errors = await verification.verify_chain_range(1, 1000)
```

### 4. Agent Discovery & Marketplace

Search and discover agents by capabilities and reputation:

```python
from uaef.agents import AgentDiscoveryService

discovery = AgentDiscoveryService(session)

# Search by capabilities
agents = await discovery.search_agents(
    capabilities=["text-generation", "web-search"],
    min_trust_score=80,
    platform=AgentPlatform.LANGCHAIN
)

# Get recommendations
recommended = await discovery.recommend_agents(
    use_case="customer_support",
    required_capabilities=["conversation", "sentiment-analysis"]
)
```

## Pilot Cockpit Dashboard

Web-based monitoring and control center:

```bash
# Start the dashboard
python cockpit/api.py

# Access at http://localhost:8080
```

**Features:**
- Real-time system statistics
- Agent registry and status
- Execution monitoring
- Ledger audit trail
- Settlement tracking
- Platform adapter health

## Configuration

Configuration via environment variables with `UAEF_` prefix:

| Variable | Description | Default |
|----------|-------------|---------|
| `UAEF_ENVIRONMENT` | Environment (development/staging/production) | development |
| `UAEF_DB_URL` | PostgreSQL connection URL | postgresql://localhost:5432/uaef |
| `UAEF_AGENT_ANTHROPIC_API_KEY` | Anthropic API key for agents | (required) |
| `UAEF_SECURITY_JWT_SECRET` | JWT signing secret | (change in production) |

See `.env.example` for all options.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_security.py -v

# Run with coverage
pytest --cov=src/uaef tests/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
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

## Roadmap

### Phase 0: Architectural Refactoring (Current) 🚧
- [x] Update README with new vision
- [ ] Rename orchestration → agents
- [ ] Define platform-agnostic models
- [ ] Create adapter framework
- [ ] Database migrations

### Phase 1: Agent Registry (Weeks 3-4)
- [ ] Agent registration service
- [ ] Discovery API
- [ ] Search and filtering
- [ ] REST API endpoints

### Phase 2: Platform Adapters (Weeks 5-8)
- [ ] LangChain adapter
- [ ] Generic/Custom adapter
- [ ] Temporal adapter
- [ ] CrewAI adapter

### Phase 3: Reputation Engine (Weeks 9-10)
- [ ] Performance tracking
- [ ] Trust score calculation
- [ ] Analytics and metrics
- [ ] Leaderboard API

### Phase 4: Marketplace (Weeks 11-12)
- [ ] Agent marketplace listing
- [ ] Transaction tracking
- [ ] Pricing models
- [ ] Creator earnings

### Phase 5: Developer SDK (Weeks 13-14)
- [ ] Python SDK
- [ ] TypeScript SDK
- [ ] CLI tool
- [ ] Documentation

### Phase 6: Enterprise Features (Weeks 15-20)
- [ ] Multi-tenancy
- [ ] Private agents
- [ ] Governance policies
- [ ] Compliance reports

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Documentation

- [Getting Started Guide](GETTING_STARTED.md)
- [Implementation Plan](UAEF_Implementation_Plan.md)
- [API Documentation](docs/api.md) (coming soon)
- [Architecture Deep Dive](docs/architecture.md) (coming soon)

## Support

- **Issues**: [GitHub Issues](https://github.com/srivarun-tech/UAEF/issues)
- **Discussions**: [GitHub Discussions](https://github.com/srivarun-tech/UAEF/discussions)

## License

MIT - See [LICENSE](LICENSE) for details

---

**UAEF** - Building the universal layer for autonomous agent coordination.
