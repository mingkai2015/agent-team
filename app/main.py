import os
import json
import time
import uuid
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models import Requirement, Task, TaskState, ApprovalRequest, WorkflowResponse
from app.database import db
from app.observability import observability
from app.evaluation import evaluation
from app.agents.skills import agent_skills
from app.agents.pm_agent import pm_agent
from app.agents.tl_agent import tl_agent
from app.agents.ux_agent import ux_agent
from app.agents.dev_agent import dev_agent
from app.agents.reviewer_agent import reviewer_agent
from app.agents.qa_agent import qa_agent
from app.agents.devops_agent import devops_agent
from app.agents.gitlab_client import gitlab_client

PHASE_ORDER = [
    "requirement", "architecture", "ux_design",
    "implementation", "review", "testing", "deployment",
]

PHASE_GATES = {
    "requirement":    {"label": "需求分析", "gate_name": "PM审批",   "agent": "PM Agent"},
    "architecture":   {"label": "架构设计", "gate_name": "架构审批", "agent": "Tech Lead Agent"},
    "ux_design":      {"label": "交互设计", "gate_name": "UX审批",   "agent": "UX Designer Agent"},
    "implementation": {"label": "代码实现", "gate_name": "代码审批", "agent": "Dev Agent"},
    "review":         {"label": "代码评审", "gate_name": "代码评审", "agent": "Code Reviewer Agent"},
    "testing":        {"label": "测试验收", "gate_name": "测试审批", "agent": "QA Engineer Agent"},
    "deployment":     {"label": "部署发布", "gate_name": "部署审批", "agent": "DevOps Agent"},
}

app = FastAPI(title="Agent Team - IT Delivery System", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    app.mount("/static", StaticFiles(directory="/app/public"), name="static")
except:
    pass


@app.get("/")
def root():
    return FileResponse("/app/public/index.html")


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


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


@app.post("/requirements", response_model=WorkflowResponse)
def create_requirement(req: Requirement):
    requirement_dict = req.model_dump()
    requirement_dict["created_at"] = datetime.now().isoformat()
    db.save_requirement(requirement_dict)

    trace_id = observability.start_trace(req.id, "pm")
    start_time = time.time()

    gitlab_issue = gitlab_client.create_issue(
        title=f"[{req.priority}] {req.title}",
        description=req.description,
        labels=["需求", req.priority],
    )

    task = Task(
        requirement_id=req.id,
        title=req.title,
        description=req.description,
        state=TaskState.ANALYZING,
        assignee="PM Agent",
    )
    task = db.save_task(task)

    try:
        spec = pm_agent.analyze(requirement_dict)
        duration = int((time.time() - start_time) * 1000)
        observability.record_agent_call(
            task.id,
            trace_id,
            "PM Agent",
            "pm",
            input_data={"requirement": requirement_dict},
            output_data=spec,
            duration_ms=duration,
        )
    except Exception as e:
        print(f"PM Agent error: {e}")
        spec = pm_agent._generate_fallback_spec(requirement_dict)
        observability.record_agent_call(
            task.id,
            trace_id,
            "PM Agent",
            "pm",
            input_data={"requirement": requirement_dict},
            output_data=spec,
            error=str(e),
        )

    task.artifacts["spec"] = spec
    task.artifacts["gitlab_issue"] = gitlab_issue
    task.artifacts["trace_id"] = trace_id
    task.artifacts["current_gate"] = "requirement"
    task.state = TaskState.PENDING_APPROVAL
    task = db.save_task(task)

    return WorkflowResponse(
        task_id=task.id,
        state=task.state.value,
        message="PM Agent 完成需求分析，已创建 GitLab Issue，等待人工审核",
        artifacts=task.artifacts,
    )


@app.get("/tasks", response_model=list)
def list_tasks():
    return db.get_all_tasks()


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks/{task_id}/approve", response_model=WorkflowResponse)
def approve_task(task_id: str, approval: ApprovalRequest):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.state != TaskState.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Task is not pending approval")

    trace_id = task.artifacts.get(
        "trace_id", f"trace-{task_id}-{int(time.time() * 1000)}"
    )

    current_phase = task.artifacts.get("current_gate")
    if not current_phase:
        raise HTTPException(status_code=400, detail="No pending gate for this task")

    gate_info = PHASE_GATES.get(current_phase, {})

    if approval.decision == "approve":
        task.state = TaskState.APPROVED
        task.approvals.append(
            {
                "stage": current_phase,
                "approver": approval.approver,
                "decision": "approved",
                "comment": approval.comment,
                "gate_name": gate_info.get("gate_name", current_phase),
                "timestamp": datetime.now().isoformat(),
            }
        )

        gitlab_issue = task.artifacts.get("gitlab_issue")
        if gitlab_issue:
            gitlab_client.update_issue(
                str(gitlab_issue.get("iid", "")), labels=["需求", "已批准"]
            )

        task = db.save_task(task)
        return _execute_next_phase(task, approval.approver, trace_id)
    else:
        task.state = TaskState.REJECTED
        task.approvals.append(
            {
                "stage": current_phase,
                "approver": approval.approver,
                "decision": "rejected",
                "comment": approval.comment,
                "gate_name": gate_info.get("gate_name", current_phase),
                "timestamp": datetime.now().isoformat(),
            }
        )
        task.artifacts["current_gate"] = None
        task = db.save_task(task)
        return WorkflowResponse(
            task_id=task.id,
            state=task.state.value,
            message=f"{gate_info.get('label', current_phase)} 审核驳回，请根据反馈修改",
            artifacts=task.artifacts,
        )


def _execute_next_phase(task: Task, approver: str, trace_id: str) -> WorkflowResponse:
    spec = task.artifacts.get("spec", {})
    implementation = task.artifacts.get("implementation", {})

    phases_completed = task.artifacts.get("phases_completed", [])

    agent_phases = [p for p in PHASE_ORDER if p != "requirement"]
    next_phase = None
    for p in agent_phases:
        if p not in phases_completed:
            next_phase = p
            break

    if next_phase is None:
        task.state = TaskState.COMPLETED
        task.artifacts["current_gate"] = None
        task = db.save_task(task)

        eval_result = evaluation.evaluate_task(task.id, task.artifacts, task.approvals)
        task.artifacts["evaluation"] = eval_result
        task = db.save_task(task)

        return WorkflowResponse(
            task_id=task.id,
            state=task.state.value,
            message="全部流程已完成，项目已交付",
            artifacts=task.artifacts,
        )

    phase_agent_map = {
        "architecture": ("Tech Lead Agent", tl_agent, "tl"),
        "ux_design": ("UX Designer Agent", ux_agent, "ux"),
        "implementation": ("Dev Agent", dev_agent, "dev"),
        "review": ("Code Reviewer Agent", reviewer_agent, "reviewer"),
        "testing": ("QA Engineer Agent", qa_agent, "qa"),
        "deployment": ("DevOps Agent", devops_agent, "devops"),
    }

    agent_name, agent, phase_key = phase_agent_map.get(
        next_phase, ("Unknown", None, "")
    )

    task.assignee = agent_name
    task = db.save_task(task)

    start_time = time.time()

    try:
        if next_phase == "architecture":
            result = agent.design(spec)
        elif next_phase == "ux_design":
            result = agent.design(spec)
        elif next_phase == "implementation":
            result = agent.implement(spec)
            if result.get("code"):
                branch_name = f"feature/{task.id[:8]}"
                gitlab_client.create_branch(branch_name)
                mr = gitlab_client.create_mr(
                    source_branch=branch_name,
                    target_branch="main",
                    title=f"Feature: {task.title}",
                    description=f"实现需求: {task.description}",
                )
                result["merge_request"] = mr
        elif next_phase == "review":
            code = implementation.get("code", [])
            result = agent.review(code, spec)
        elif next_phase == "testing":
            result = agent.test(spec, implementation)
        elif next_phase == "deployment":
            result = agent.deploy(spec, implementation)

            code = implementation.get("code", [])
            if code:
                push_result = gitlab_client.push_code(
                    code, task.title, f"feature/{task.id[:8]}"
                )
                result["gitlab_push"] = push_result
        else:
            result = {}

        duration = int((time.time() - start_time) * 1000)
        observability.record_agent_call(
            task.id,
            trace_id,
            agent_name,
            phase_key,
            input_data={"spec": spec},
            output_data=result,
            duration_ms=duration,
        )

        task.artifacts[next_phase] = result

    except Exception as e:
        print(f"{agent_name} error: {e}")

        fallback_method = getattr(agent, f"_fallback_{next_phase}", None)
        if fallback_method:
            result = fallback_method(spec)
        else:
            result = {}

        duration = int((time.time() - start_time) * 1000)
        observability.record_agent_call(
            task.id,
            trace_id,
            agent_name,
            phase_key,
            input_data={"spec": spec},
            output_data=result,
            error=str(e),
            duration_ms=duration,
        )

        task.artifacts[next_phase] = result

    task.artifacts.setdefault("phases_completed", []).append(next_phase)
    task.artifacts["current_gate"] = next_phase
    task.state = TaskState.PENDING_APPROVAL
    task = db.save_task(task)

    gate_info = PHASE_GATES.get(next_phase, {})
    phase_messages = {
        "architecture": f"TL Agent 完成架构设计，等待{gate_info.get('gate_name', '审批')}",
        "ux_design": f"UX Designer 完成交互设计，等待{gate_info.get('gate_name', '审批')}",
        "implementation": f"Dev Agent 完成代码实现，已创建 MR，等待{gate_info.get('gate_name', '审批')}",
        "review": f"Code Reviewer 完成代码评审，等待{gate_info.get('gate_name', '审批')}",
        "testing": f"QA Agent 完成测试，等待{gate_info.get('gate_name', '审批')}",
        "deployment": f"DevOps Agent 完成部署配置，等待{gate_info.get('gate_name', '审批')}",
    }

    return WorkflowResponse(
        task_id=task.id,
        state=task.state.value,
        message=phase_messages.get(next_phase, f"{agent_name} 完成"),
        artifacts=task.artifacts,
    )


@app.get("/tasks/{task_id}/spec")
def get_task_spec(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.artifacts.get("spec", {})


@app.get("/tasks/{task_id}/implementation")
def get_task_implementation(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.artifacts.get("implementation", {})


@app.get("/tasks/{task_id}/architecture")
def get_task_architecture(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.artifacts.get("architecture", {})


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
    return task.artifacts.get("test_report", {})


@app.get("/tasks/{task_id}/deployment")
def get_task_deployment(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.artifacts.get("deployment", {})


@app.get("/phases")
def get_phases():
    return {"phase_order": PHASE_ORDER, "gates": PHASE_GATES}


@app.get("/gitlab/status")
def gitlab_status():
    return {
        "mode": os.getenv("GITLAB_MODE", "mock"),
        "base_url": os.getenv("GITLAB_URL", "https://gitlab.com"),
    }
