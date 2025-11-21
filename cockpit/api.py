"""
UAEF Pilot Cockpit - FastAPI Backend

Web API for controlling and monitoring UAEF:
- Agents management
- Workflow orchestration
- Real-time monitoring
- Settlement tracking
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from uaef.core import get_session, configure_logging
from uaef.agents import AgentRegistry, WorkflowService, ClaudeAgentExecutor
from uaef.agents.models import WorkflowDefinition, Agent
from uaef.ledger import LedgerEventService
from uaef.settlement import SettlementService
from sqlalchemy import select

# Configure logging
configure_logging()

# Create FastAPI app
app = FastAPI(
    title="UAEF Pilot Cockpit",
    description="Control center for Universal Autonomous Enterprise Fabric",
    version="0.1.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class AgentCreate(BaseModel):
    name: str
    agent_type: str = "claude"
    capabilities: List[str]
    model: Optional[str] = "claude-sonnet-4-20250514"


class AgentResponse(BaseModel):
    id: str
    name: str
    agent_type: str
    status: str
    capabilities: List[str]
    model: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowTask(BaseModel):
    name: str
    task_type: str
    agent_type: str
    config: dict
    dependencies: List[str] = []


class WorkflowCreate(BaseModel):
    name: str
    description: str
    tasks: List[WorkflowTask]


class WorkflowExecute(BaseModel):
    workflow_id: str
    input_data: dict = {}


class SystemStats(BaseModel):
    total_agents: int
    active_agents: int
    total_workflows: int
    total_executions: int
    total_events: int
    pending_settlements: int


# Root endpoint - serve dashboard
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the pilot cockpit dashboard."""
    html_path = Path(__file__).parent / "dashboard.html"
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return "<h1>UAEF Pilot Cockpit</h1><p>Dashboard loading...</p>"


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "operational", "timestamp": datetime.now().isoformat()}


# System statistics
@app.get("/api/stats", response_model=SystemStats)
async def get_system_stats():
    """Get system-wide statistics."""
    async with get_session() as session:
        # Count agents
        agents_result = await session.execute(select(Agent))
        agents = agents_result.scalars().all()
        total_agents = len(agents)
        active_agents = len([a for a in agents if a.status == "active"])

        # Count workflows
        workflows_result = await session.execute(select(WorkflowDefinition))
        workflows = workflows_result.scalars().all()
        total_workflows = len(workflows)

        # Count executions
        from uaef.agents.models import WorkflowExecution
        executions_result = await session.execute(select(WorkflowExecution))
        executions = executions_result.scalars().all()
        total_executions = len(executions)

        # Count events
        from uaef.ledger.models import LedgerEvent
        events_result = await session.execute(select(LedgerEvent))
        events = events_result.scalars().all()
        total_events = len(events)

        # Count pending settlements
        from uaef.settlement.models import SettlementSignal
        settlements_result = await session.execute(
            select(SettlementSignal).where(SettlementSignal.status == "pending")
        )
        settlements = settlements_result.scalars().all()
        pending_settlements = len(settlements)

        return SystemStats(
            total_agents=total_agents,
            active_agents=active_agents,
            total_workflows=total_workflows,
            total_executions=total_executions,
            total_events=total_events,
            pending_settlements=pending_settlements,
        )


# Agent endpoints
@app.get("/api/agents", response_model=List[AgentResponse])
async def list_agents():
    """List all agents."""
    async with get_session() as session:
        agent_registry = AgentRegistry(session)
        agents = await agent_registry.list_agents()
        return [AgentResponse.model_validate(agent) for agent in agents]


@app.post("/api/agents", response_model=AgentResponse)
async def create_agent(agent_data: AgentCreate):
    """Register a new agent."""
    async with get_session() as session:
        agent_registry = AgentRegistry(session)
        agent, api_key = await agent_registry.register_agent(
            name=agent_data.name,
            agent_type=agent_data.agent_type,
            capabilities=agent_data.capabilities,
            model=agent_data.model,
        )
        await agent_registry.activate_agent(agent.id)
        await session.commit()
        await session.refresh(agent)
        return AgentResponse.model_validate(agent)


@app.post("/api/agents/{agent_id}/activate")
async def activate_agent(agent_id: str):
    """Activate an agent."""
    async with get_session() as session:
        agent_registry = AgentRegistry(session)
        await agent_registry.activate_agent(agent_id)
        await session.commit()
        return {"status": "activated", "agent_id": agent_id}


@app.post("/api/agents/{agent_id}/deactivate")
async def deactivate_agent(agent_id: str):
    """Deactivate an agent."""
    async with get_session() as session:
        agent_registry = AgentRegistry(session)
        await agent_registry.deactivate_agent(agent_id)
        await session.commit()
        return {"status": "deactivated", "agent_id": agent_id}


# Workflow endpoints
@app.get("/api/workflows")
async def list_workflows():
    """List all workflow definitions."""
    async with get_session() as session:
        result = await session.execute(select(WorkflowDefinition))
        workflows = result.scalars().all()
        return [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "task_count": len(w.tasks),
                "is_active": w.is_active,
                "created_at": w.created_at.isoformat(),
            }
            for w in workflows
        ]


@app.post("/api/workflows")
async def create_workflow(workflow_data: WorkflowCreate):
    """Create a new workflow definition."""
    async with get_session() as session:
        workflow_def = WorkflowDefinition(
            name=workflow_data.name,
            description=workflow_data.description,
            tasks=[task.model_dump() for task in workflow_data.tasks],
            is_active=True,
        )
        session.add(workflow_def)
        await session.commit()
        await session.refresh(workflow_def)
        return {
            "id": workflow_def.id,
            "name": workflow_def.name,
            "status": "created",
        }


@app.post("/api/workflows/execute")
async def execute_workflow(execution_data: WorkflowExecute):
    """Execute a workflow."""
    async with get_session() as session:
        workflow_service = WorkflowService(session)
        execution = await workflow_service.start_workflow(
            definition_id=execution_data.workflow_id,
            input_data=execution_data.input_data,
            initiated_by="cockpit",
        )
        await session.commit()
        await session.refresh(execution)
        return {
            "execution_id": execution.id,
            "workflow_id": execution_data.workflow_id,
            "status": execution.status,
            "created_at": execution.created_at.isoformat(),
        }


# Execution monitoring
@app.get("/api/executions")
async def list_executions(limit: int = 20):
    """List recent workflow executions."""
    async with get_session() as session:
        from uaef.agents.models import WorkflowExecution
        result = await session.execute(
            select(WorkflowExecution)
            .order_by(WorkflowExecution.created_at.desc())
            .limit(limit)
        )
        executions = result.scalars().all()
        return [
            {
                "id": e.id,
                "workflow_definition_id": e.definition_id,
                "status": e.status,
                "created_at": e.created_at.isoformat(),
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            }
            for e in executions
        ]


@app.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution details with events."""
    async with get_session() as session:
        from uaef.agents.models import WorkflowExecution
        ledger_service = LedgerEventService(session)

        result = await session.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        events = await ledger_service.get_events_by_workflow(execution_id)

        return {
            "id": execution.id,
            "workflow_definition_id": execution.definition_id,
            "status": execution.status,
            "input_data": execution.input_data,
            "output_data": execution.output_data,
            "created_at": execution.created_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "events": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "sequence": e.sequence_number,
                    "created_at": e.created_at.isoformat(),
                    "payload": e.payload,
                }
                for e in events
            ],
        }


# Ledger events
@app.get("/api/events")
async def list_events(limit: int = 50):
    """List recent ledger events."""
    async with get_session() as session:
        from uaef.ledger.models import LedgerEvent
        result = await session.execute(
            select(LedgerEvent)
            .order_by(LedgerEvent.sequence_number.desc())
            .limit(limit)
        )
        events = result.scalars().all()
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "sequence": e.sequence_number,
                "workflow_id": e.workflow_id,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]


# Settlement endpoints
@app.get("/api/settlements")
async def list_settlements(status: Optional[str] = None):
    """List settlement signals."""
    async with get_session() as session:
        settlement_service = SettlementService(session)
        from uaef.settlement.models import SettlementStatus

        status_filter = SettlementStatus(status) if status else None
        signals = await settlement_service.list_signals(status=status_filter)

        return [
            {
                "id": s.id,
                "workflow_execution_id": s.workflow_execution_id,
                "amount": float(s.amount),
                "currency": s.currency,
                "status": s.status,
                "recipient_id": s.recipient_id,
                "created_at": s.created_at.isoformat(),
            }
            for s in signals
        ]


if __name__ == "__main__":
    import uvicorn
    print("=" * 80)
    print("UAEF PILOT COCKPIT")
    print("=" * 80)
    print("\nStarting web server...")
    print("Dashboard: http://localhost:8080")
    print("API Docs: http://localhost:8080/docs")
    print("\nPress CTRL+C to stop")
    print("=" * 80)

    uvicorn.run(app, host="0.0.0.0", port=8080)
