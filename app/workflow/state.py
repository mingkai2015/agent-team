"""LangGraph workflow state definition."""

from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict


def _merge_dict(old: dict, new: dict) -> dict:
    merged = {**old}
    merged.update(new)
    return merged


class WorkflowState(TypedDict, total=False):
    # Task identity
    task_id: str
    project_id: str
    requirement: dict

    # Agent outputs — each phase writes its own key
    spec: Annotated[dict, _merge_dict]
    architecture: Annotated[dict, _merge_dict]
    ux_design: Annotated[dict, _merge_dict]
    implementation: Annotated[dict, _merge_dict]
    review: Annotated[dict, _merge_dict]
    testing: Annotated[dict, _merge_dict]
    deployment: Annotated[dict, _merge_dict]

    # Flow control
    current_phase: str
    approval_status: str          # "pending" | "approved" | "rejected"
    approval_comment: str
    retry_count: int
    phases_completed: Annotated[list, operator.add]

    # Observability
    trace_id: str
    gitlab_issue: dict
    evaluation: dict
    error: Optional[str]
