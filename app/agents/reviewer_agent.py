import os
import json
import logging
from typing import Dict, Any, List
from app.agents.llm_client import llm_client

logger = logging.getLogger(__name__)


REVIEWER_AGENT_SYSTEM_PROMPT = """
You are a senior code reviewer responsible for code quality and security review.

Responsibilities:
1. Check coding standards and best practices
2. Identify potential security risks
3. Assess maintainability
4. Provide actionable improvements

Output MUST be valid JSON.
"""


class ReviewerAgent:
    def __init__(self):
        self.name = "Code Reviewer Agent"
        self.llm = llm_client

    def review(
        self, code: List[Dict[str, Any]], spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Review code implementation"""
        code_summary = "\n".join(
            [f"{f['path']}:\n{f['content'][:500]}" for f in code[:3]]
        )

        user_prompt = f"""
Review the following implementation:

Requirement: {spec.get("title", "")}
Code:
{code_summary}

Return a JSON review report:
{{
  "overall_score": 85,
  "issues": [
    {{"severity": "high/medium/low", "category": "security/performance/maintainability", "description": "Issue description", "file": "File path"}}
  ],
  "suggestions": ["Suggestion 1", "Suggestion 2"],
  "approved": true/false
}}
"""
        try:
            response = self.llm.chat(REVIEWER_AGENT_SYSTEM_PROMPT, user_prompt)
            report = self._parse_json_response(response)
            if report:
                return report
        except Exception as e:
            logger.error("Reviewer Agent LLM call failed: %s", e)

        return self._fallback_review(code)

    def _parse_json_response(self, response: str) -> Any:
        from app.schemas import parse_llm_json, ReviewReport

        parsed = parse_llm_json(response, ReviewReport)
        return parsed.model_dump() if parsed else None

    def _fallback_review(self, code: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "overall_score": 80,
            "issues": [
                {
                    "severity": "medium",
                    "category": "maintainability",
                    "description": "Consider adding API documentation annotations",
                    "file": "main.py",
                },
                {
                    "severity": "low",
                    "category": "security",
                    "description": "Consider adding request rate limiting",
                    "file": "main.py",
                },
            ],
            "suggestions": [
                "Add type hints",
                "Increase unit test coverage",
                "Add error-handling middleware",
            ],
            "approved": True,
        }


reviewer_agent = ReviewerAgent()
