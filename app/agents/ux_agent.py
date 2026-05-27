import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from app.agents.llm_client import LLMClient

logger = logging.getLogger(__name__)


UX_AGENT_SYSTEM_PROMPT = """
You are a senior UX designer responsible for user experience and UI interaction design.

Responsibilities:
1. Analyze user interaction scenarios in the requirement
2. Design information architecture and user flows
3. Create wireframe/prototype descriptions
4. Define layouts and interaction patterns
5. Ensure consistency and usability

Tech stack:
- Frontend: React + TypeScript + Vite
- Design tool: Figma (describe design guidelines)

Output MUST be valid JSON.
"""


class UXAgent:
    def __init__(self):
        self.name = "UX Agent"
        self.llm = LLMClient()

    def design(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate UX design based on requirements"""
        title = spec.get("title", "")
        description = spec.get("detailed_description", "")
        user_stories = spec.get("user_stories", [])

        prompt = f"""
Generate a UX design proposal for the requirement "{title}":

Requirement description: {description}
User stories: {json.dumps(user_stories)}

Return JSON:
{{
  "information_architecture": {{
    "pages": ["Page 1", "Page 2"],
    "navigation": "Navigation structure description"
  }},
  "user_flows": [
    {{"name": "Flow 1", "steps": ["Step 1", "Step 2"]}}
  ],
  "wireframes": [
    {{"page": "Page 1", "elements": ["Element 1", "Element 2"], "layout": "Layout description"}}
  ],
  "interaction_patterns": ["Pattern 1", "Pattern 2"],
  "design_system": {{
    "colors": ["Primary", "Secondary"],
    "typography": "Typography guidelines",
    "spacing": "Spacing guidelines"
  }}
}}
"""
        try:
            response = self.llm.chat(UX_AGENT_SYSTEM_PROMPT, prompt)
            design = self._parse_json_response(response)
            if design:
                return design
        except Exception as e:
            logger.error("UX Agent LLM call failed: %s", e)

        return self._fallback_design(spec)

    def _parse_json_response(self, response: str) -> Any:
        from app.schemas import parse_llm_json, UXDesign

        parsed = parse_llm_json(response, UXDesign)
        return parsed.model_dump() if parsed else None

    def _fallback_design(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "information_architecture": {
                "pages": ["Home", "List", "Detail", "Form"],
                "navigation": "Top navigation + sidebar menu",
            },
            "user_flows": [
                {"name": "Primary flow", "steps": ["Sign in", "Browse", "Act", "Return"]}
            ],
            "wireframes": [
                {
                    "page": "Home",
                    "elements": ["Header", "Hero", "Content list", "Footer"],
                    "layout": "Single-column, responsive",
                },
                {
                    "page": "List",
                    "elements": ["Search bar", "Filters", "Data table", "Pagination"],
                    "layout": "Left filters + right results",
                },
                {
                    "page": "Detail",
                    "elements": ["Basic info", "Action buttons", "Details"],
                    "layout": "Card-based layout",
                },
            ],
            "interaction_patterns": [
                "Pull-to-refresh",
                "Infinite scroll",
                "Modal confirmation",
                "Form validation",
                "Loading states",
            ],
            "design_system": {
                "colors": {
                    "primary": "#007bff",
                    "secondary": "#6c757d",
                    "success": "#28a745",
                    "danger": "#dc3545",
                    "background": "#ffffff",
                    "text": "#333333",
                },
                "typography": {
                    "font_family": "system-ui, -apple-system, sans-serif",
                    "heading": "bold 24px/20px",
                    "body": "normal 14px",
                },
                "spacing": {
                    "xs": "4px",
                    "sm": "8px",
                    "md": "16px",
                    "lg": "24px",
                    "xl": "32px",
                },
            },
            "created_at": datetime.now().isoformat(),
        }


ux_agent = UXAgent()
