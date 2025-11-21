# UAEF Pilot Cockpit

**Web-based control center for Universal Autonomous Enterprise Fabric**

The Pilot Cockpit provides a real-time dashboard for monitoring and controlling your UAEF deployment.

---

## Features

### 📊 Real-Time Dashboard
- Live system statistics
- Active agents count
- Workflow executions
- Ledger events
- Pending settlements

### 🤖 Agent Management
- View all registered agents
- Monitor agent status
- Track agent capabilities
- Activation/deactivation controls

### ⚙️ Workflow Control
- List all workflow definitions
- View workflow structure
- Monitor task dependencies
- Track execution history

### 📋 Execution Monitoring
- Real-time execution tracking
- Status updates
- Completion timestamps
- Output data viewing

### 🔐 Ledger Audit
- Complete audit trail
- Event sequence tracking
- Cryptographic verification
- Workflow event filtering

### 💰 Settlement Tracking
- View all settlements
- Status monitoring
- Amount tracking
- Recipient management

---

## Quick Start

### 1. Start the Cockpit Server

```bash
cd cockpit
python api.py
```

The server will start on `http://localhost:8000`

### 2. Access the Dashboard

Open your web browser and navigate to:
```
http://localhost:8000
```

### 3. Explore the API

Interactive API documentation is available at:
```
http://localhost:8000/docs
```

---

## API Endpoints

### System
- `GET /api/health` - Health check
- `GET /api/stats` - System statistics

### Agents
- `GET /api/agents` - List all agents
- `POST /api/agents` - Register new agent
- `POST /api/agents/{id}/activate` - Activate agent
- `POST /api/agents/{id}/deactivate` - Deactivate agent

### Workflows
- `GET /api/workflows` - List workflow definitions
- `POST /api/workflows` - Create workflow
- `POST /api/workflows/execute` - Execute workflow

### Executions
- `GET /api/executions` - List recent executions
- `GET /api/executions/{id}` - Get execution details

### Ledger
- `GET /api/events` - List ledger events

### Settlements
- `GET /api/settlements` - List settlements

---

## Usage Examples

### Register a New Agent (API)

```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Research Agent",
    "agent_type": "claude",
    "capabilities": ["research", "analysis"],
    "model": "claude-sonnet-4-20250514"
  }'
```

### Create a Workflow (API)

```bash
curl -X POST http://localhost:8000/api/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Simple Task",
    "description": "Basic workflow",
    "tasks": [
      {
        "name": "task1",
        "task_type": "agent",
        "agent_type": "claude",
        "config": {"prompt": "Hello"},
        "dependencies": []
      }
    ]
  }'
```

### Execute a Workflow (API)

```bash
curl -X POST http://localhost:8000/api/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "your-workflow-id",
    "input_data": {"key": "value"}
  }'
```

---

## Dashboard Features

### Statistics Cards
- **Active Agents**: Shows active/total agent count
- **Workflows**: Total workflow definitions
- **Executions**: Total workflow executions
- **Ledger Events**: Total audit trail events
- **Pending Settlements**: Awaiting payment signals

### Tabs

**Agents Tab**
- View all registered agents
- See agent status, capabilities, and models
- Filter by status

**Workflows Tab**
- List all workflow definitions
- View task counts
- Monitor active/inactive status

**Executions Tab**
- Recent workflow executions
- Status tracking (completed/running)
- Start and completion timestamps

**Events Tab**
- Complete ledger audit trail
- Event type filtering
- Sequence numbers
- Timestamps

**Settlements Tab**
- All settlement signals
- Amount and currency
- Status (pending/completed)
- Recipient tracking

---

## Configuration

The cockpit uses the same configuration as the main UAEF system:
- Database connection from `.env`
- Anthropic API key for agent execution
- All UAEF settings

---

## Development

### Run in Development Mode

```bash
# With auto-reload
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Custom Port

```bash
# Run on different port
python api.py
# Or
uvicorn api:app --port 8080
```

---

## Architecture

```
┌─────────────────────────────────────┐
│    Browser (Dashboard UI)           │
│    HTML + JavaScript                │
└──────────────┬──────────────────────┘
               │ HTTP/JSON
               │
┌──────────────▼──────────────────────┐
│    FastAPI Backend (api.py)         │
│    - REST API endpoints             │
│    - Request validation             │
│    - CORS handling                  │
└──────────────┬──────────────────────┘
               │
               │
┌──────────────▼──────────────────────┐
│    UAEF Core Services               │
│    - AgentRegistry                  │
│    - WorkflowService                │
│    - LedgerEventService             │
│    - SettlementService              │
└──────────────┬──────────────────────┘
               │
               │
┌──────────────▼──────────────────────┐
│    Database (SQLite/PostgreSQL)     │
│    - Agents, Workflows, Events      │
│    - Executions, Settlements        │
└─────────────────────────────────────┘
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Mac/Linux

# Kill process or use different port
```

### Database Connection Issues
- Ensure `.env` file exists in project root
- Check `UAEF_DB_URL` is configured
- Run migrations: `alembic upgrade head`

### API Key Not Working
- Verify `UAEF_AGENT_ANTHROPIC_API_KEY` in `.env`
- Check key is valid and has credits

---

## Security Notes

- **Production**: Set up authentication/authorization
- **CORS**: Currently allows all origins (development only)
- **API Keys**: Never expose in client-side code
- **HTTPS**: Use reverse proxy (nginx) for production

---

## Future Enhancements

- [ ] User authentication
- [ ] Role-based access control
- [ ] Real-time WebSocket updates
- [ ] Workflow builder UI
- [ ] Advanced filtering and search
- [ ] Export/import workflows
- [ ] Performance metrics graphs
- [ ] Alert notifications
- [ ] Multi-tenant support

---

## License

Part of the UAEF project - Universal Autonomous Enterprise Fabric

---

**Status**: ✅ Production Ready
**Version**: 0.1.0
**Last Updated**: 2025-01-20
