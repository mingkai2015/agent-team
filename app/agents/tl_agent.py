import os
import json
import logging
from typing import Dict, Any, List
from app.agents.llm_client import llm_client

logger = logging.getLogger(__name__)


TL_AGENT_SYSTEM_PROMPT = """
You are a senior technical lead responsible for system architecture design and technology selection.

Responsibilities:
1. Analyze requirements and design the system architecture
2. Choose an appropriate tech stack
3. Design APIs and data models
4. Assess technical risks

Output MUST be valid JSON.
"""


class TechLeadAgent:
    def __init__(self):
        self.name = "Tech Lead Agent"
        self.llm = llm_client

    def design(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical architecture and design"""
        user_prompt = f"""
Create a technical architecture/design proposal for the following requirement:

Title: {spec.get("title", "")}
Details: {spec.get("detailed_description", "")}
User stories: {json.dumps(spec.get("user_stories", []))}

Return JSON:
{{
  "architecture": "Architecture description",
  "tech_stack": ["Tech stack items"],
  "api_design": ["API design notes"],
  "data_model": ["Data model notes"],
  "security": ["Security considerations"],
  "risks": ["Technical risks"],
  "milestones": ["Milestones"]
}}
"""
        try:
            response = self.llm.chat(TL_AGENT_SYSTEM_PROMPT, user_prompt)
            design = self._parse_json_response(response)
            if design:
                return design
        except Exception as e:
            logger.error("TL Agent LLM call failed: %s", e)

        return self._fallback_design(spec)

    def _parse_json_response(self, response: str) -> Any:
        from app.schemas import parse_llm_json, ArchitectureDesign

        parsed = parse_llm_json(response, ArchitectureDesign)
        return parsed.model_dump() if parsed else None

    def _fallback_design(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "architecture": "Microservice-style architecture with REST APIs",
            "tech_stack": ["Python 3.11", "FastAPI", "PostgreSQL", "Redis", "Docker"],
            "api_design": [
                "RESTful API conventions",
                "Versioning: /api/v1/",
                "Auth: JWT bearer token",
                "Pagination: limit/offset",
            ],
            "data_model": [
                "Warehouse: (id, name, location)",
                "Product: (id, sku, name, category)",
                "Inventory: (id, warehouse_id, product_id, quantity)",
                "Transaction: (id, type, product_id, quantity, timestamp)",
            ],
            "security": ["AuthZ/AuthN", "Input validation", "SQL injection protection", "Audit logging"],
            "risks": ["High-concurrency inventory updates may require distributed locking", "Multi-warehouse consistency"],
            "milestones": ["Environment setup", "Data model design", "API implementation", "Testing", "Deployment"],
        }


tl_agent = TechLeadAgent()
