import json
from datetime import datetime
from typing import Dict, Any, List
from app.agents.llm_client import LLMClient


UX_AGENT_SYSTEM_PROMPT = """
你是一个资深交互设计师，负责用户体验和界面设计。

你的职责：
1. 分析需求中的用户交互场景
2. 设计产品信息架构和用户流程
3. 创建线框图和交互原型描述
4. 定义界面布局和交互模式
5. 确保用户体验的一致性和可用性

技术栈：
- 前端：React + TypeScript + Vite
- 设计工具：Figma（描述设计规范）

输出必须为有效的 JSON 格式。
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
请为需求「{title}」生成 UX 设计方案：

需求描述：{description}
用户故事：{json.dumps(user_stories)}

请生成 JSON 格式的 UX 设计：
{{
  "information_architecture": {{
    "pages": ["页面1", "页面2"],
    "navigation": "导航结构描述"
  }},
  "user_flows": [
    {{"name": "流程1", "steps": ["步骤1", "步骤2"]}}
  ],
  "wireframes": [
    {{"page": "页面1", "elements": ["元素1", "元素2"], "layout": "布局描述"}}
  ],
  "interaction_patterns": ["模式1", "模式2"],
  "design_system": {{
    "colors": ["主色", "辅色"],
    "typography": "字体规范",
    "spacing": "间距规范"
  }}
}}
"""
        try:
            response = self.llm.chat(UX_AGENT_SYSTEM_PROMPT, prompt)
            design = self._parse_json_response(response)
            if design:
                return design
        except Exception as e:
            print(f"UX Agent LLM call failed: {e}")

        return self._fallback_design(spec)

    def _parse_json_response(self, response: str) -> Any:
        import re

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return None

    def _fallback_design(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "information_architecture": {
                "pages": ["首页", "列表页", "详情页", "表单页"],
                "navigation": "顶部导航 + 侧边栏菜单",
            },
            "user_flows": [
                {"name": "主流程", "steps": ["登录", "浏览", "操作", "返回"]}
            ],
            "wireframes": [
                {
                    "page": "首页",
                    "elements": ["Header", "Hero区域", "内容列表", "Footer"],
                    "layout": "单列布局，响应式",
                },
                {
                    "page": "列表页",
                    "elements": ["搜索栏", "筛选器", "数据表格", "分页"],
                    "layout": "左侧筛选 + 右侧列表",
                },
                {
                    "page": "详情页",
                    "elements": ["基本信息", "操作按钮", "详情内容"],
                    "layout": "卡片式布局",
                },
            ],
            "interaction_patterns": [
                "下拉刷新",
                "无限滚动",
                "模态框确认",
                "表单验证",
                "加载状态",
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
