"""Agent Team — FastAPI application with LangGraph workflow engine."""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.auth import AuthMiddleware
from app.database import db
from app.logging_config import setup_logging
from app.models import (
    ApprovalRequest,
    Project,
    Requirement,
    Task,
    TaskState,
    WorkflowResponse,
)
from app.observability import observability
from app.evaluation import evaluation
from app.agents.skills import agent_skills
from app.agents.gitlab_client import GitLabClient
from app.workflow.graph import PHASE_GATES, PHASE_ORDER, compile_workflow

setup_logging()
logger = logging.getLogger(__name__)

# ── LangGraph workflow (compiled once at startup) ─────────
workflow = compile_workflow()

# ── FastAPI app ───────────────────────────────────────────
app = FastAPI(title="Agent Team - IT Delivery System", version="1.0.0")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

import pathlib
_public_dir = pathlib.Path(__file__).resolve().parent.parent / "public"
if not _public_dir.exists():
    _public_dir = pathlib.Path("/app/public")

_assets_dir = _public_dir / "assets"
_index_html = _public_dir / "index.html"

if _assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="static-assets")


def _get_gitlab_client(project_id: str = None) -> GitLabClient:
    if project_id:
        project = db.get_project(project_id)
        if project:
            return GitLabClient({
                "gitlab_url": project.gitlab_url,
                "gitlab_token": project.gitlab_token or "",
                "gitlab_project_id": project.gitlab_project_id,
                "gitlab_repo_url": project.gitlab_repo_url or "",
                "gitlab_mode": project.gitlab_mode,
                "main_branch": project.main_branch,
            })
    return GitLabClient()


def _sync_task_from_graph(task: Task, graph_state: dict) -> Task:
    """Write relevant graph state back into the Task model for persistence."""
    for key in ("spec", "architecture", "ux_design", "implementation",
                "review", "testing", "deployment", "evaluation"):
        if key in graph_state and graph_state[key]:
            task.artifacts[key] = graph_state[key]
    task.artifacts["current_gate"] = graph_state.get("current_phase")
    task.artifacts["phases_completed"] = graph_state.get("phases_completed", [])
    task.artifacts["trace_id"] = graph_state.get("trace_id", "")
    if "gitlab_issue" in graph_state:
        task.artifacts["gitlab_issue"] = graph_state["gitlab_issue"]
    return task


# ── Health ────────────────────────────────────────────────

@app.get("/")
def root():
    if _index_html.exists():
        return FileResponse(str(_index_html))
    return {"message": "Agent Team API", "docs": "/docs"}


@app.get("/health")
def health():
    checks = {"api": "ok"}
    try:
        db.redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks, "timestamp": datetime.now().isoformat()}


# ── Skills / Observability / Evaluation ───────────────────

@app.get("/skills")
def get_skills():
    return agent_skills.get_all_skills()


@app.get("/skills/constitution")
def get_constitution():
    return {"constitution": agent_skills.get_constitution()}


@app.get("/observability/metrics")
def get_metrics():
    return observability.get_metrics()


@app.get("/observability/trace/{task_id}")
def get_trace(task_id: str):
    return {"trace": observability.get_trace(task_id)}


@app.get("/evaluation")
def get_evaluation_summary():
    return {
        "total_tasks": len(evaluation.evaluations),
        "average_score": round(evaluation.get_average_score(), 1),
        "grade_distribution": evaluation.get_grade_distribution(),
    }


@app.get("/evaluation/{task_id}")
def get_task_evaluation(task_id: str):
    eval_result = evaluation.get_task_evaluation(task_id)
    if not eval_result:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return eval_result


# ── Workflow: create requirement → LangGraph ──────────────

@app.post("/requirements", response_model=WorkflowResponse)
def create_requirement(req: Requirement):
    if not req.project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    project = db.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    requirement_dict = req.model_dump()
    requirement_dict["created_at"] = datetime.now().isoformat()
    db.save_requirement(requirement_dict)

    trace_id = observability.start_trace(req.id, "pm")

    gl_client = _get_gitlab_client(req.project_id)
    gitlab_issue = gl_client.create_issue(
        title=f"[{req.priority}] {req.title}",
        description=req.description,
        labels=["requirement", req.priority],
    )

    task = Task(
        project_id=req.project_id,
        requirement_id=req.id,
        title=req.title,
        description=req.description,
        state=TaskState.ANALYZING,
        assignee="PM Agent",
    )
    task = db.save_task(task)

    config = {"configurable": {"thread_id": task.id}}
    initial_state = {
        "task_id": task.id,
        "project_id": req.project_id,
        "requirement": requirement_dict,
        "trace_id": trace_id,
        "gitlab_issue": gitlab_issue,
        "retry_count": 0,
        "phases_completed": [],
    }

    logger.info("Starting workflow for task %s", task.id)
    result = workflow.invoke(initial_state, config)

    task = _sync_task_from_graph(task, result)
    task.state = TaskState.PENDING_APPROVAL
    task.assignee = PHASE_GATES.get(result.get("current_phase", ""), {}).get("agent", "PM Agent")
    task = db.save_task(task)

    return WorkflowResponse(
        task_id=task.id,
        state=task.state.value,
        message="PM Agent completed requirement analysis. Awaiting human approval.",
        artifacts=task.artifacts,
    )


# ── Workflow: approve / reject → resume LangGraph ─────────

@app.post("/tasks/{task_id}/approve", response_model=WorkflowResponse)
def approve_task(task_id: str, approval: ApprovalRequest):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.state != TaskState.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Task is not pending approval")

    current_phase = task.artifacts.get("current_gate")
    if not current_phase:
        raise HTTPException(status_code=400, detail="No pending gate for this task")

    gate_info = PHASE_GATES.get(current_phase, {})

    task.approvals.append({
        "stage": current_phase,
        "approver": approval.approver,
        "decision": approval.decision,
        "comment": approval.comment,
        "gate_name": gate_info.get("gate_name", current_phase),
        "timestamp": datetime.now().isoformat(),
    })

    config = {"configurable": {"thread_id": task_id}}

    status = "approved" if approval.decision == "approve" else "rejected"
    workflow.update_state(config, {
        "approval_status": status,
        "approval_comment": approval.comment or "",
    }, as_node="human_review")

    logger.info("Resuming workflow for task %s (decision=%s, phase=%s)",
                task_id, approval.decision, current_phase)
    result = workflow.invoke(None, config)

    task = _sync_task_from_graph(task, result)
    new_phase = result.get("current_phase", "")

    if new_phase == "completed":
        task.state = TaskState.COMPLETED
        message = "Workflow completed. Project delivery is ready."
    elif approval.decision != "approve":
        task.state = TaskState.PENDING_APPROVAL
        message = f"{gate_info.get('label', current_phase)} was rejected. The agent has reworked the output; awaiting re-approval."
    else:
        task.state = TaskState.PENDING_APPROVAL
        new_gate = PHASE_GATES.get(new_phase, {})
        task.assignee = new_gate.get("agent", "")
        message = f"{new_gate.get('agent', '')} completed {new_gate.get('label', '')}. Awaiting {new_gate.get('gate_name', 'approval')}."

    task = db.save_task(task)

    return WorkflowResponse(
        task_id=task.id,
        state=task.state.value,
        message=message,
        artifacts=task.artifacts,
    )


# ── SSE streaming ─────────────────────────────────────────

@app.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """SSE endpoint: stream graph execution events in real-time."""
    config = {"configurable": {"thread_id": task_id}}

    async def event_generator():
        try:
            async for event in workflow.astream_events(None, config, version="v2"):
                event_data = {
                    "type": event.get("event", ""),
                    "name": event.get("name", ""),
                    "data": str(event.get("data", ""))[:500],
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Retry rejected task ──────────────────────────────────

@app.post("/tasks/{task_id}/retry", response_model=WorkflowResponse)
def retry_task(task_id: str):
    task = db.get_task(task_id)
    if not task or task.state not in (TaskState.REJECTED, TaskState.FAILED):
        raise HTTPException(status_code=400, detail="Task is not in a retryable state")

    config = {"configurable": {"thread_id": task_id}}
    workflow.update_state(config, {
        "approval_status": "approved",
        "retry_count": (task.artifacts.get("retry_count", 0)) + 1,
    }, as_node="human_review")

    result = workflow.invoke(None, config)
    task = _sync_task_from_graph(task, result)
    task.state = TaskState.PENDING_APPROVAL
    task = db.save_task(task)

    return WorkflowResponse(
        task_id=task.id,
        state=task.state.value,
        message=f"Task resubmitted. Current phase: {result.get('current_phase', '')}",
        artifacts=task.artifacts,
    )


# ── Tasks CRUD ────────────────────────────────────────────

@app.get("/tasks", response_model=list)
def list_tasks(project_id: Optional[str] = None):
    return db.get_all_tasks(project_id)


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ── Artifact endpoints ────────────────────────────────────

@app.get("/tasks/{task_id}/spec")
def get_task_spec(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.artifacts.get("spec", {})


@app.get("/tasks/{task_id}/architecture")
def get_task_architecture(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.artifacts.get("architecture", {})


@app.get("/tasks/{task_id}/implementation")
def get_task_implementation(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.artifacts.get("implementation", {})


@app.get("/tasks/{task_id}/review")
def get_task_review(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.artifacts.get("review", {})


@app.get("/tasks/{task_id}/test-report")
def get_task_test_report(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.artifacts.get("testing", {})


@app.get("/tasks/{task_id}/deployment")
def get_task_deployment(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.artifacts.get("deployment", {})


# ── Phases / Workflow info ────────────────────────────────

@app.get("/phases")
def get_phases():
    return {"phase_order": PHASE_ORDER, "gates": PHASE_GATES}


@app.get("/workflow/graph")
def get_workflow_graph():
    try:
        graph = workflow.get_graph()
        return {"mermaid": graph.draw_mermaid()}
    except Exception as e:
        return {"error": str(e)}


@app.get("/gitlab/status")
def gitlab_status():
    return {
        "mode": os.getenv("GITLAB_MODE", "mock"),
        "base_url": os.getenv("GITLAB_URL", "https://gitlab.com"),
    }


# ── Projects CRUD ─────────────────────────────────────────

@app.get("/projects", response_model=list)
def list_projects():
    return db.get_all_projects()


@app.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/projects", response_model=Project)
def create_project(project: Project):
    return db.save_project(project)


@app.put("/projects/{project_id}", response_model=Project)
def update_project(project_id: str, project: Project):
    existing = db.get_project(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")
    project.id = project_id
    return db.save_project(project)


@app.delete("/projects/{project_id}")
def delete_project(project_id: str):
    existing = db.get_project(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete_project(project_id)
    return {"message": "Project deleted"}


@app.get("/projects/{project_id}/gitlab/test")
def test_gitlab_connection(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    gl_client = _get_gitlab_client(project_id)
    if gl_client.mode == "mock":
        return {"status": "success", "mode": "mock", "message": "Mock mode is enabled"}
    try:
        test_result = gl_client.create_issue(
            title="Test Connection",
            description="This is a test issue to verify GitLab connection",
            labels=["test"],
        )
        if "error" in test_result:
            return {"status": "error", "message": test_result.get("error")}
        return {"status": "success", "message": "GitLab connection successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── SPA catch-all (must be LAST route) ───────────────────

@app.get("/{full_path:path}")
def spa_catch_all(full_path: str):
    """Serve React SPA for client-side routes."""
    if _index_html.exists():
        return FileResponse(str(_index_html))
    raise HTTPException(status_code=404, detail="Not found")
