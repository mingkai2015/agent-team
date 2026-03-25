import os
import json
from typing import Dict, Any, List


AGENT_SKILLS = {
    "pm_agent": {
        "name": "Product Manager",
        "description": "需求分析、User Story 拆解、验收标准定义",
        "capabilities": [
            "需求理解与澄清",
            "User Story 编写",
            "验收标准定义",
            "工作量估算",
            "优先级排序",
        ],
        "tools": ["llm", "spec_generator", "estimation_tool"],
        "rules": [
            "每个需求必须有明确验收标准",
            "User Story 格式: 作为[角色],我希望[功能],以便[价值]",
            "工作量评估使用 T-shirt sizing (S/M/L)",
        ],
    },
    "tl_agent": {
        "name": "Tech Lead",
        "description": "系统架构设计、技术选型、方案评审",
        "capabilities": [
            "架构设计",
            "技术选型",
            "API 设计",
            "数据模型设计",
            "风险评估",
        ],
        "tools": ["llm", "architecture_tool", "api_designer"],
        "rules": [
            "优先使用成熟稳定技术栈",
            "API 设计遵循 RESTful 规范",
            "必须包含安全设计",
        ],
    },
    "dev_agent": {
        "name": "Developer",
        "description": "代码实现、单元测试、代码自测",
        "capabilities": ["Spec Kit 工作流", "代码生成", "单元测试编写", "代码自测"],
        "tools": ["llm", "spec_kit", "code_generator", "test_generator"],
        "rules": ["遵循项目编码规范", "必须包含单元测试", "代码必须通过 lint 检查"],
    },
    "reviewer_agent": {
        "name": "Code Reviewer",
        "description": "代码质量审查、安全检查、改进建议",
        "capabilities": [
            "代码规范检查",
            "安全漏洞扫描",
            "性能优化建议",
            "代码可维护性评估",
        ],
        "tools": ["llm", "static_analyzer", "security_scanner"],
        "rules": ["严重问题必须修复", "建议性问题尽量修复", "评审通过率目标 > 80%"],
    },
    "qa_agent": {
        "name": "QA Engineer",
        "description": "测试用例设计、功能测试、缺陷管理",
        "capabilities": ["测试用例设计", "功能测试执行", "回归测试", "缺陷报告"],
        "tools": ["llm", "test_generator", "bug_tracker"],
        "rules": ["验收标准必须 100% 覆盖", "关键路径必须通过测试", "缺陷必须可复现"],
    },
    "devops_agent": {
        "name": "DevOps",
        "description": "CI/CD 配置、部署自动化、监控设置",
        "capabilities": ["Docker 配置", "CI/CD 流水线", "部署脚本", "健康检查"],
        "tools": ["llm", "docker_tool", "ci_cd_tool", "deploy_tool"],
        "rules": ["必须包含健康检查", "必须支持回滚", "部署必须可重复"],
    },
}


CONSTITUTION = """
# Agent Team 宪法

## 核心原则
1. **质量第一** - 代码质量 > 开发速度
2. **可追溯** - 所有决策必须有据可查
3. **可审计** - 人工审核是必须的
4. **可回滚** - 任何变更必须可回滚

## Agent 协作规则
1. 每个 Agent 必须记录输入输出
2. 失败时记录错误原因和重试次数
3. 下一阶段必须验证上一阶段产出

## 质量标准
- 单元测试覆盖率 > 80%
- 代码评审通过率 > 80%
- 验收标准覆盖率 100%
- 部署成功率 > 95%

## 安全规则
1. 不记录敏感信息（如密码、token）
2. 代码执行在隔离环境
3. 外部 API 调用有超时限制
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
