import os
import json
from datetime import datetime
from typing import Dict, Any
from app.models import Task, TaskState
from app.agents.llm_client import llm_client


PM_AGENT_SYSTEM_PROMPT = """
你是一个资深产品经理，负责需求分析和拆解。
你的职责：
1. 理解用户需求，补充遗漏信息
2. 将需求拆解为可执行的 User Stories
3. 定义清晰的验收标准
4. 评估工作量

输出必须为有效的 JSON 格式，包含以下字段：
{
  "detailed_description": "详细的需求描述",
  "user_stories": ["用户故事1", "用户故事2"],
  "acceptance_criteria": ["验收标准1", "验收标准2"],
  "estimation": "S/M/L (小/中/大)"
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
请分析以下需求，生成结构化的需求规格文档：

需求标题：{requirement.get("title", "")}
需求描述：{requirement.get("description", "")}
优先级：{requirement.get("priority", "P2")}

请生成包含详细描述、用户故事、验收标准和工作量估算的 JSON 文档。
"""

        try:
            response = self.llm.chat(PM_AGENT_SYSTEM_PROMPT, user_prompt)
            spec = self._parse_llm_response(response, requirement)
        except Exception as e:
            print(f"LLM call failed, using fallback: {e}")
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
            "detailed_description": f"## 需求详情\n\n### 背景\n{title} 的业务需求\n\n### 功能描述\n{desc}",
            "user_stories": [
                f"作为用户，我希望{title}，以便{desc}",
                "作为系统管理员，我希望管理配置，以便系统正常运行",
                "作为测试人员，我希望有验收标准，以便验证功能",
            ],
            "acceptance_criteria": [
                f"功能 {title} 能够正常使用",
                "系统响应时间在可接受范围内",
                "关键操作有日志记录",
                "异常情况有错误提示",
            ],
            "estimation": "M" if len(desc) < 200 else "L",
            "priority": requirement.get("priority", "P2"),
        }


pm_agent = PMAgent()
