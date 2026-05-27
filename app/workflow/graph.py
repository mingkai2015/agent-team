"""Build and compile the LangGraph delivery workflow."""

import logging
import os

from langgraph.graph import StateGraph, START, END

from app.workflow.state import WorkflowState
from app.workflow.nodes import (
    pm_node, tl_node, ux_node, dev_node,
    reviewer_node, qa_node, devops_node,
    design_dispatch_node, human_review_node, finalize_node,
)

logger = logging.getLogger(__name__)

PHASE_GATES = {
    "requirement":      {"label": "Requirement analysis", "gate_name": "PM approval",           "agent": "PM Agent"},
    "architecture":     {"label": "Architecture design",  "gate_name": "Architecture approval", "agent": "Tech Lead Agent"},
    "ux_design":        {"label": "UX design",            "gate_name": "UX approval",           "agent": "UX Designer Agent"},
    "design_complete":  {"label": "Design complete",      "gate_name": "Design approval",       "agent": "Design Team"},
    "implementation":   {"label": "Implementation",       "gate_name": "Code approval",         "agent": "Dev Agent"},
    "review":           {"label": "Code review",          "gate_name": "Code review",           "agent": "Code Reviewer Agent"},
    "testing":          {"label": "QA testing",           "gate_name": "Test approval",         "agent": "QA Engineer Agent"},
    "deployment":       {"label": "Deployment",           "gate_name": "Deployment approval",   "agent": "DevOps Agent"},
}

PHASE_ORDER = [
    "requirement", "architecture", "ux_design",
    "implementation", "review", "testing", "deployment",
]

_PHASE_TO_NODE = {
    "requirement": "pm",
    "architecture": "tl",
    "ux_design": "ux",
    "design_complete": "dev",
    "implementation": "dev",
    "review": "reviewer",
    "testing": "qa",
    "deployment": "devops",
}

_REWORK_TARGET = {
    "review": "dev",
    "testing": "dev",
}

MAX_AUTO_REWORK = 3


# ── Routing functions ─────────────────────────────────────

def _route_after_review(state: WorkflowState) -> str:
    """Conditional edge after human_review: approve→next, reject→rework."""
    if state.get("approval_status") == "approved":
        phase = state.get("current_phase", "")
        node = _PHASE_TO_NODE.get(phase)

        if phase == "requirement":
            return "design_dispatch"
        if phase in ("architecture", "ux_design", "design_complete"):
            return "dev"
        if phase == "implementation":
            return "reviewer"
        if phase == "review":
            return "qa"
        if phase == "testing":
            return "devops"
        if phase == "deployment":
            return "finalize"
        return "finalize"

    phase = state.get("current_phase", "")
    target = _REWORK_TARGET.get(phase, _PHASE_TO_NODE.get(phase, "pm"))
    return target


def _route_after_code_review(state: WorkflowState) -> str:
    """Auto-gate after reviewer: if not approved and retries < MAX, rework dev."""
    review = state.get("review", {})
    if review.get("approved") is True:
        return "human_review"
    retry = state.get("retry_count", 0)
    if retry < MAX_AUTO_REWORK:
        return "dev"
    return "human_review"


def _design_join(state: WorkflowState) -> dict:
    """Join node after parallel TL + UX complete."""
    return {"current_phase": "design_complete"}


# ── Graph builders ────────────────────────────────────────

def build_workflow(template: str = "full") -> StateGraph:
    """Construct the delivery workflow graph.

    Templates:
        full  — all 7 agents, TL+UX parallel, reviewer auto-rework
        fast  — skip UX + QA, no auto-rework
        review_only — PM + Dev + Reviewer only
    """
    wf = StateGraph(WorkflowState)

    wf.add_node("pm", pm_node)
    wf.add_node("human_review", human_review_node)
    wf.add_node("finalize", finalize_node)

    if template == "full":
        wf.add_node("design_dispatch", design_dispatch_node)
        wf.add_node("dev", dev_node)
        wf.add_node("reviewer", reviewer_node)
        wf.add_node("qa", qa_node)
        wf.add_node("devops", devops_node)

        wf.add_edge(START, "pm")
        wf.add_edge("pm", "human_review")
        wf.add_edge("design_dispatch", "human_review")
        wf.add_edge("dev", "human_review")

        # Reviewer: auto-rework if score low + retries < MAX
        wf.add_conditional_edges("reviewer", _route_after_code_review, {
            "human_review": "human_review",
            "dev": "dev",
        })

        wf.add_edge("qa", "human_review")
        wf.add_edge("devops", "human_review")
        wf.add_edge("finalize", END)

        wf.add_conditional_edges(
            "human_review",
            _route_after_review,
            {
                "pm": "pm",
                "design_dispatch": "design_dispatch",
                "dev": "dev",
                "reviewer": "reviewer",
                "qa": "qa",
                "devops": "devops",
                "finalize": "finalize",
            },
        )

    elif template == "fast":
        wf.add_node("tl", tl_node)
        wf.add_node("dev", dev_node)
        wf.add_node("reviewer", reviewer_node)
        wf.add_node("devops", devops_node)

        wf.add_edge(START, "pm")
        wf.add_edge("pm", "human_review")
        wf.add_edge("tl", "human_review")
        wf.add_edge("dev", "human_review")
        wf.add_edge("reviewer", "human_review")
        wf.add_edge("devops", "human_review")
        wf.add_edge("finalize", END)

        def _fast_route(state):
            if state.get("approval_status") != "approved":
                phase = state.get("current_phase", "")
                return _REWORK_TARGET.get(phase, _PHASE_TO_NODE.get(phase, "pm"))
            phase = state.get("current_phase", "")
            seq = {"requirement": "tl", "architecture": "dev",
                   "implementation": "reviewer", "review": "devops",
                   "deployment": "finalize"}
            return seq.get(phase, "finalize")

        wf.add_conditional_edges("human_review", _fast_route, {
            "pm": "pm", "tl": "tl", "dev": "dev",
            "reviewer": "reviewer", "devops": "devops", "finalize": "finalize",
        })

    elif template == "review_only":
        wf.add_node("dev", dev_node)
        wf.add_node("reviewer", reviewer_node)

        wf.add_edge(START, "pm")
        wf.add_edge("pm", "human_review")
        wf.add_edge("dev", "human_review")
        wf.add_edge("reviewer", "human_review")
        wf.add_edge("finalize", END)

        def _review_route(state):
            if state.get("approval_status") != "approved":
                return _PHASE_TO_NODE.get(state.get("current_phase", ""), "pm")
            phase = state.get("current_phase", "")
            seq = {"requirement": "dev", "implementation": "reviewer",
                   "review": "finalize"}
            return seq.get(phase, "finalize")

        wf.add_conditional_edges("human_review", _review_route, {
            "pm": "pm", "dev": "dev", "reviewer": "reviewer", "finalize": "finalize",
        })

    return wf


def compile_workflow(checkpointer=None, template: str = "full"):
    """Compile graph. If checkpointer is None, try Redis then fall back to memory."""
    wf = build_workflow(template)

    if checkpointer is None:
        try:
            from langgraph.checkpoint.redis import RedisSaver
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            checkpointer = RedisSaver(redis_url=redis_url)
            checkpointer.setup()
            logger.info("Using Redis checkpointer at %s", redis_url)
        except Exception as e:
            logger.warning("Redis checkpointer unavailable (%s), falling back to MemorySaver", e)
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()

    return wf.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )
