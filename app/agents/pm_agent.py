import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
from app.models import Task, TaskState
from app.agents.llm_client import llm_client

logger = logging.getLogger(__name__)


PM_AGENT_SYSTEM_PROMPT = """
You are a senior product manager responsible for requirement analysis and decomposition.

Responsibilities:
1. Understand the user need and fill in missing details
2. Decompose the requirement into executable user stories
3. Define clear acceptance criteria
4. Estimate effort

Output MUST be valid JSON with the following fields:
{
  "detailed_description": "Detailed requirement description",
  "user_stories": ["User story 1", "User story 2"],
  "acceptance_criteria": ["Acceptance criteria 1", "Acceptance criteria 2"],
  "estimation": "S/M/L"
}
"""


class PMAgent:
    def __init__(self):
        self.name = "PM Agent"
        self.llm = llm_client

    def analyze(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze requirement using LLM and generate SPEC.md
        """
        user_prompt = f"""
Analyze the following requirement and generate a structured requirement spec document:

Title: {requirement.get("title", "")}
Description: {requirement.get("description", "")}
Priority: {requirement.get("priority", "P2")}

Return a JSON document containing detailed_description, user_stories, acceptance_criteria, and estimation.
"""

        try:
            response = self.llm.chat(PM_AGENT_SYSTEM_PROMPT, user_prompt)
            spec = self._parse_llm_response(response, requirement)
        except Exception as e:
            logger.error("LLM call failed, using fallback: %s", e)
            spec = self._generate_fallback_spec(requirement)

        spec["analyzed_at"] = datetime.now().isoformat()
        return spec

    def _parse_llm_response(self, response: str, requirement: Dict) -> Dict:
        from app.schemas import parse_llm_json, PMSpec

        parsed = parse_llm_json(response, PMSpec)
        if parsed:
            return {
                "requirement_id": requirement.get("id", ""),
                "title": requirement.get("title", ""),
                "description": requirement.get("description", ""),
                "detailed_description": parsed.detailed_description,
                "user_stories": parsed.user_stories,
                "acceptance_criteria": parsed.acceptance_criteria,
                "estimation": parsed.estimation,
                "priority": requirement.get("priority", "P2"),
            }
        return self._generate_fallback_spec(requirement)

    def _generate_fallback_spec(self, requirement: Dict) -> Dict:
        desc = requirement.get("description", "")
        title = requirement.get("title", "")
        return {
            "requirement_id": requirement.get("id", ""),
            "title": title,
            "description": desc,
            "detailed_description": f"## Requirement details\n\n### Background\nBusiness need for {title}\n\n### Functional description\n{desc}",
            "user_stories": [
                f"As a user, I want {title} so that {desc}",
                "As a system administrator, I want to manage configuration so the system runs reliably",
                "As a tester, I want clear acceptance criteria so I can verify the feature",
            ],
            "acceptance_criteria": [
                f"The {title} feature works end-to-end",
                "System response time is within an acceptable range",
                "Key operations are logged",
                "Errors are surfaced with clear messages",
            ],
            "estimation": "M" if len(desc) < 200 else "L",
            "priority": requirement.get("priority", "P2"),
        }


pm_agent = PMAgent()
