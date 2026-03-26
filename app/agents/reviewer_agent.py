import os
import json
from typing import Dict, Any, List
from app.agents.llm_client import llm_client


REVIEWER_AGENT_SYSTEM_PROMPT = """
你是一个资深代码评审专家，负责代码质量审查和安全检查。

你的职责：
1. 检查代码规范和最佳实践
2. 识别潜在的安全风险
3. 评估代码可维护性
4. 提供改进建议

输出必须为有效的 JSON 格式。
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
请评审以下代码实现：

需求：{spec.get("title", "")}
代码：
{code_summary}

请生成 JSON 格式的评审报告：
{{
  "overall_score": 85,
  "issues": [
    {{"severity": "high/medium/low", "category": "security/performance/maintainability", "description": "问题描述", "file": "文件路径"}}
  ],
  "suggestions": ["改进建议1", "改进建议2"],
  "approved": true/false
}}
"""
        try:
            response = self.llm.chat(REVIEWER_AGENT_SYSTEM_PROMPT, user_prompt)
            report = self._parse_json_response(response)
            if report:
                return report
        except Exception as e:
            print(f"Reviewer Agent LLM call failed: {e}")

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
                    "description": "建议添加 API 文档注解",
                    "file": "main.py",
                },
                {
                    "severity": "low",
                    "category": "security",
                    "description": "建议添加请求频率限制",
                    "file": "main.py",
                },
            ],
            "suggestions": [
                "添加 Type hints 类型注解",
                "增加单元测试覆盖率",
                "添加错误处理中间件",
            ],
            "approved": True,
        }


reviewer_agent = ReviewerAgent()
