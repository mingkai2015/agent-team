from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from uuid import uuid4


class TaskState(str, Enum):
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def generate_id() -> str:
    return str(uuid4())


class Requirement(BaseModel):
    id: str = Field(default_factory=generate_id)
    project_id: Optional[str] = None
    title: str
    description: str
    priority: str = "P2"
    created_at: datetime = Field(default_factory=datetime.now)


class Task(BaseModel):
    id: str = Field(default_factory=generate_id)
    project_id: Optional[str] = None
    requirement_id: str
    title: str
    description: str
    state: TaskState = TaskState.CREATED
    assignee: Optional[str] = None
    artifacts: dict = Field(default_factory=dict)
    approvals: List[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ApprovalRequest(BaseModel):
    approver: str
    decision: str  # "approve" or "reject"
    comment: Optional[str] = None


class WorkflowResponse(BaseModel):
    task_id: str
    state: str
    message: str
    artifacts: Optional[dict] = None


class Project(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    description: str = ""
    gitlab_url: str = "https://gitlab.com"
    gitlab_token: Optional[str] = None
    gitlab_project_id: str = ""
    gitlab_repo_url: Optional[str] = None
    gitlab_mode: str = "mock"
    main_branch: str = "main"
    workflow_template: str = "full"
    created_at: datetime = Field(default_factory=datetime.now)
