import os
import json
from typing import Dict, Any, List


AGENT_SKILLS = {
    "pm_agent": {
        "name": "Product Manager",
        "description": "Requirement analysis, user story decomposition, acceptance criteria definition",
        "capabilities": [
            "Requirement clarification",
            "User story writing",
            "Acceptance criteria definition",
            "Effort estimation",
            "Priority ordering",
        ],
        "tools": ["llm", "spec_generator", "estimation_tool"],
        "rules": [
            "Each requirement must have explicit acceptance criteria",
            "User story format: As a [role], I want [capability] so that [value]",
            "Use T-shirt sizing for estimation (S/M/L)",
        ],
    },
    "tl_agent": {
        "name": "Tech Lead",
        "description": "System architecture design, technology selection, design reviews",
        "capabilities": [
            "Architecture design",
            "Technology selection",
            "API design",
            "Data model design",
            "Risk assessment",
        ],
        "tools": ["llm", "architecture_tool", "api_designer"],
        "rules": [
            "Prefer mature and stable technologies",
            "Follow RESTful conventions for API design",
            "Include security considerations",
        ],
    },
    "dev_agent": {
        "name": "Developer",
        "description": "Implementation, unit tests, self-validation",
        "capabilities": ["Spec Kit workflow", "Code generation", "Unit test writing", "Self-validation"],
        "tools": ["llm", "spec_kit", "code_generator", "test_generator"],
        "rules": ["Follow project coding standards", "Include unit tests", "Code must pass lint checks"],
    },
    "reviewer_agent": {
        "name": "Code Reviewer",
        "description": "Code quality review, security review, improvement suggestions",
        "capabilities": [
            "Coding standards checks",
            "Security vulnerability scanning",
            "Performance improvement suggestions",
            "Maintainability assessment",
        ],
        "tools": ["llm", "static_analyzer", "security_scanner"],
        "rules": ["Fix critical issues", "Fix non-critical issues when reasonable", "Target review pass rate > 80%"],
    },
    "qa_agent": {
        "name": "QA Engineer",
        "description": "Test design, functional testing, defect management",
        "capabilities": ["Test case design", "Functional testing", "Regression testing", "Defect reporting"],
        "tools": ["llm", "test_generator", "bug_tracker"],
        "rules": ["Acceptance criteria must be fully covered", "Critical paths must pass tests", "Defects must be reproducible"],
    },
    "devops_agent": {
        "name": "DevOps",
        "description": "CI/CD configuration, deployment automation, monitoring setup",
        "capabilities": ["Docker configuration", "CI/CD pipelines", "Deployment scripts", "Health checks"],
        "tools": ["llm", "docker_tool", "ci_cd_tool", "deploy_tool"],
        "rules": ["Include health checks", "Support rollback", "Deployments must be repeatable"],
    },
}


CONSTITUTION = """
# Agent Team Constitution

## Core principles
1. **Quality first** — code quality > speed
2. **Traceability** — decisions must be explainable and reviewable
3. **Auditability** — human approval is mandatory
4. **Rollbackability** — every change must be reversible

## Agent collaboration rules
1. Each agent must record inputs and outputs
2. On failure, record the error and retry count
3. Each phase must validate the previous phase's artifacts

## Quality standards
- Unit test coverage > 80%
- Review pass rate > 80%
- Acceptance criteria coverage 100%
- Deployment success rate > 95%

## Security rules
1. Do not log sensitive information (passwords, tokens, etc.)
2. Execute code in an isolated environment
3. Enforce timeouts for external API calls
"""


class AgentSkills:
    def __init__(self):
        self.skills = AGENT_SKILLS
        self.constitution = CONSTITUTION

    def get_skill(self, agent_name: str) -> Dict[str, Any]:
        return self.skills.get(agent_name, {})

    def get_all_skills(self) -> Dict[str, Any]:
        return self.skills

    def get_constitution(self) -> str:
        return self.constitution

    def get_tools_for_agent(self, agent_name: str) -> List[str]:
        skill = self.get_skill(agent_name)
        return skill.get("tools", [])

    def get_rules_for_agent(self, agent_name: str) -> List[str]:
        skill = self.get_skill(agent_name)
        return skill.get("rules", [])


agent_skills = AgentSkills()
