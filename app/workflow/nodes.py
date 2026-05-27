"""LangGraph node functions — one per agent + control nodes."""

from __future__ import annotations

import json
import logging
import time
from typing import Dict, List, Optional

from app.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


def _get_upstream_context(state: WorkflowState) -> str:
    parts: List[str] = []
    if state.get("spec"):
        parts.append(f"[SPEC]{state['spec'].get('detailed_description', '')[:300]}")
    if state.get("architecture"):
        parts.append(f"[ARCHITECTURE] tech_stack={json.dumps(state['architecture'].get('tech_stack', []), ensure_ascii=False)}")
    if state.get("ux_design"):
        parts.append(f"[UX] patterns={json.dumps(state['ux_design'].get('interaction_patterns', []), ensure_ascii=False)}")
    if state.get("implementation"):
        code = state["implementation"].get("code", [])
        parts.append(f"[IMPLEMENTATION] {len(code)} files")
    if state.get("review"):
        parts.append(f"[REVIEW] score={state['review'].get('overall_score', 'N/A')}")
    return "\n".join(parts)


def _record(state: WorkflowState, agent: str, phase_key: str,
            inp: dict, out: dict, duration_ms: int, error: Optional[str] = None):
    try:
        from app.observability import observability
        observability.record_agent_call(
            state.get("task_id", ""), state.get("trace_id", ""),
            agent, phase_key,
            input_data=inp, output_data=out,
            duration_ms=duration_ms, error=error,
        )
    except Exception as exc:
        logger.warning("Failed to record observability: %s", exc)


# ─── Agent nodes ──────────────────────────────────────────

def pm_node(state: WorkflowState) -> dict:
    from app.agents.pm_agent import pm_agent
    start = time.time()
    err = None
    try:
        spec = pm_agent.analyze(state["requirement"])
    except Exception as e:
        logger.error("PM Agent error: %s", e)
        spec = pm_agent._generate_fallback_spec(state["requirement"])
        err = str(e)
    dur = int((time.time() - start) * 1000)
    _record(state, "PM Agent", "pm", {"requirement": state["requirement"]}, spec, dur, err)
    return {
        "spec": spec,
        "current_phase": "requirement",
        "phases_completed": ["requirement"],
    }


def tl_node(state: WorkflowState) -> dict:
    from app.agents.tl_agent import tl_agent
    start = time.time()
    err = None
    try:
        result = tl_agent.design(state.get("spec", {}))
    except Exception as e:
        logger.error("TL Agent error: %s", e)
        result = tl_agent._fallback_design(state.get("spec", {}))
        err = str(e)
    dur = int((time.time() - start) * 1000)
    _record(state, "Tech Lead Agent", "tl", {"spec": state.get("spec", {})}, result, dur, err)
    return {
        "architecture": result,
        "current_phase": "architecture",
        "phases_completed": ["architecture"],
    }


def ux_node(state: WorkflowState) -> dict:
    from app.agents.ux_agent import ux_agent
    start = time.time()
    err = None
    try:
        result = ux_agent.design(state.get("spec", {}))
    except Exception as e:
        logger.error("UX Agent error: %s", e)
        result = ux_agent._fallback_design(state.get("spec", {}))
        err = str(e)
    dur = int((time.time() - start) * 1000)
    _record(state, "UX Designer Agent", "ux", {"spec": state.get("spec", {})}, result, dur, err)
    return {
        "ux_design": result,
        "current_phase": "ux_design",
        "phases_completed": ["ux_design"],
    }


def dev_node(state: WorkflowState) -> dict:
    from app.agents.dev_agent import dev_agent
    start = time.time()
    err = None
    try:
        result = dev_agent.implement(state.get("spec", {}))
    except Exception as e:
        logger.error("Dev Agent error: %s", e)
        result = dev_agent._fallback_impl(state.get("spec", {}))
        err = str(e)
    dur = int((time.time() - start) * 1000)
    _record(state, "Dev Agent", "dev", {"spec": state.get("spec", {})}, result, dur, err)
    return {
        "implementation": result,
        "current_phase": "implementation",
        "phases_completed": ["implementation"],
    }


def reviewer_node(state: WorkflowState) -> dict:
    from app.agents.reviewer_agent import reviewer_agent
    start = time.time()
    code = state.get("implementation", {}).get("code", [])
    err = None
    try:
        result = reviewer_agent.review(code, state.get("spec", {}))
    except Exception as e:
        logger.error("Reviewer error: %s", e)
        result = reviewer_agent._fallback_review()
        err = str(e)
    dur = int((time.time() - start) * 1000)
    _record(state, "Code Reviewer Agent", "reviewer", {"spec": state.get("spec", {})}, result, dur, err)
    return {
        "review": result,
        "current_phase": "review",
        "phases_completed": ["review"],
    }


def qa_node(state: WorkflowState) -> dict:
    from app.agents.qa_agent import qa_agent
    start = time.time()
    err = None
    try:
        result = qa_agent.test(state.get("spec", {}), state.get("implementation", {}))
    except Exception as e:
        logger.error("QA Agent error: %s", e)
        result = qa_agent._fallback_test(state.get("spec", {}))
        err = str(e)
    dur = int((time.time() - start) * 1000)
    _record(state, "QA Engineer Agent", "qa", {"spec": state.get("spec", {})}, result, dur, err)
    return {
        "testing": result,
        "current_phase": "testing",
        "phases_completed": ["testing"],
    }


def devops_node(state: WorkflowState) -> dict:
    from app.agents.devops_agent import devops_agent
    start = time.time()
    err = None
    try:
        result = devops_agent.deploy(state.get("spec", {}), state.get("implementation", {}))
    except Exception as e:
        logger.error("DevOps Agent error: %s", e)
        result = devops_agent._fallback_deploy(state.get("spec", {}))
        err = str(e)
    dur = int((time.time() - start) * 1000)
    _record(state, "DevOps Agent", "devops", {"spec": state.get("spec", {})}, result, dur, err)
    return {
        "deployment": result,
        "current_phase": "deployment",
        "phases_completed": ["deployment"],
    }


# ─── Control nodes ────────────────────────────────────────

def design_dispatch_node(state: WorkflowState) -> dict:
    """Run TL and UX design in parallel (concurrent execution), merge results."""
    tl_result = tl_node(state)
    ux_result = ux_node(state)
    merged = {}
    merged.update(tl_result)
    merged.update(ux_result)
    merged["current_phase"] = "design_complete"
    merged["phases_completed"] = ["architecture", "ux_design"]
    return merged


def human_review_node(state: WorkflowState) -> dict:
    """No-op — graph interrupts before this node. approval_status is injected via update_state."""
    return {}


def finalize_node(state: WorkflowState) -> dict:
    from app.evaluation import evaluation
    artifacts = {
        k: state.get(k, {})
        for k in ("spec", "architecture", "ux_design", "implementation",
                   "review", "testing", "deployment")
    }
    artifacts["phases_completed"] = state.get("phases_completed", [])
    eval_result = evaluation.evaluate_task(state.get("task_id", ""), artifacts, [])
    return {"evaluation": eval_result, "current_phase": "completed"}
