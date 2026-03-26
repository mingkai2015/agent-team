"""Pydantic schemas for validating LLM agent outputs."""

import json
import re
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def parse_llm_json(raw: str, schema: Type[T]) -> Optional[T]:
    """Extract JSON from LLM response text and validate against a Pydantic schema.

    Returns the validated model instance, or None if parsing/validation fails.
    """
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        json_match = re.search(r"\[[\s\S]*\]", raw)
    if not json_match:
        logger.warning("No JSON block found in LLM response (len=%d)", len(raw))
        return None
    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.warning("JSON decode error: %s", e)
        return None
    try:
        return schema.model_validate(data)
    except ValidationError as e:
        logger.warning("Schema validation failed for %s: %s", schema.__name__, e)
        return None


# ── PM Agent ──────────────────────────────────────────────

class PMSpec(BaseModel):
    detailed_description: str = ""
    user_stories: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    estimation: str = "M"


# ── Tech Lead Agent ───────────────────────────────────────

class ArchitectureDesign(BaseModel):
    architecture: str = ""
    tech_stack: List[str] = Field(default_factory=list)
    api_design: List[str] = Field(default_factory=list)
    data_model: List[str] = Field(default_factory=list)
    security: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    milestones: List[str] = Field(default_factory=list)


# ── UX Agent ──────────────────────────────────────────────

class UXDesign(BaseModel):
    information_architecture: Optional[Dict[str, Any]] = None
    user_flows: List[Dict[str, Any]] = Field(default_factory=list)
    wireframes: List[Dict[str, Any]] = Field(default_factory=list)
    interaction_patterns: List[str] = Field(default_factory=list)
    design_system: Optional[Dict[str, Any]] = None


# ── Dev Agent ─────────────────────────────────────────────

class DevPlan(BaseModel):
    architecture: str = ""
    tech_stack: List[str] = Field(default_factory=list)
    api_design: List[str] = Field(default_factory=list)
    data_model: List[str] = Field(default_factory=list)
    milestones: List[str] = Field(default_factory=list)


class DevTask(BaseModel):
    id: str
    description: str
    phase: str = ""
    status: str = "pending"


class CodeFile(BaseModel):
    path: str
    content: str
    language: str = ""


# ── Reviewer Agent ────────────────────────────────────────

class ReviewIssue(BaseModel):
    severity: str = "medium"
    category: str = ""
    description: str = ""
    file: str = ""


class ReviewReport(BaseModel):
    overall_score: int = 0
    issues: List[ReviewIssue] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    approved: bool = False


# ── QA Agent ──────────────────────────────────────────────

class TestCase(BaseModel):
    id: str
    name: str
    description: str = ""
    steps: List[str] = Field(default_factory=list)
    expected: str = ""


class TestResult(BaseModel):
    case_id: str
    status: str
    notes: str = ""


class QATestReport(BaseModel):
    test_cases: List[TestCase] = Field(default_factory=list)
    test_results: List[TestResult] = Field(default_factory=list)
    coverage: str = ""
    summary: str = ""
