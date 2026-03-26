import os
import json
from typing import Dict, Any, List
from app.agents.llm_client import llm_client


TL_AGENT_SYSTEM_PROMPT = """
你是一个资深技术负责人，负责系统架构设计和技术选型。

你的职责：
1. 分析需求，设计系统架构
2. 选择合适的技术栈
3. 设计 API 接口和数据模型
4. 评估技术风险

输出必须为有效的 JSON 格式。
"""


class TechLeadAgent:
    def __init__(self):
        self.name = "Tech Lead Agent"
        self.llm = llm_client

    def design(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical architecture and design"""
        user_prompt = f"""
请为以下需求生成技术架构设计方案：

需求：{spec.get("title", "")}
详情：{spec.get("detailed_description", "")}
用户故事：{json.dumps(spec.get("user_stories", []))}

请生成 JSON 格式的架构设计：
{{
  "architecture": "系统架构描述",
  "tech_stack": ["技术栈列表"],
  "api_design": ["API 设计要点"],
  "data_model": ["数据模型设计"],
  "security": ["安全考虑"],
  "risks": ["技术风险评估"],
  "milestones": ["里程碑列表"]
}}
"""
        try:
            response = self.llm.chat(TL_AGENT_SYSTEM_PROMPT, user_prompt)
            design = self._parse_json_response(response)
            if design:
                return design
        except Exception as e:
            print(f"TL Agent LLM call failed: {e}")

        return self._fallback_design(spec)

    def _parse_json_response(self, response: str) -> Any:
        from app.schemas import parse_llm_json, ArchitectureDesign

        parsed = parse_llm_json(response, ArchitectureDesign)
        return parsed.model_dump() if parsed else None

    def _fallback_design(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "architecture": "微服务架构，使用 REST API",
            "tech_stack": ["Python 3.11", "FastAPI", "PostgreSQL", "Redis", "Docker"],
            "api_design": [
                "RESTful API 设计规范",
                "版本管理: /api/v1/",
                "认证: JWT Token",
                "分页: limit/offset",
            ],
            "data_model": [
                "Warehouse: 仓库(id, name, location)",
                "Product: 商品(id, sku, name, category)",
                "Inventory: 库存(id, warehouse_id, product_id, quantity)",
                "Transaction: 流水(id, type, product_id, quantity, timestamp)",
            ],
            "security": ["API 认证与授权", "输入校验", "SQL 注入防护", "日志审计"],
            "risks": ["高并发库存扣减需考虑分布式锁", "多仓库数据一致性"],
            "milestones": ["环境搭建", "数据模型设计", "API 实现", "测试", "部署"],
        }


tl_agent = TechLeadAgent()
