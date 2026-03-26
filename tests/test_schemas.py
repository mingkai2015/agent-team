"""Unit tests for the Pydantic schema validation layer."""

from app.schemas import (
    parse_llm_json,
    PMSpec,
    ArchitectureDesign,
    ReviewReport,
    QATestReport,
    UXDesign,
)


class TestParseLLMJson:
    def test_clean_json(self):
        raw = '{"detailed_description": "desc", "user_stories": ["s1"], "acceptance_criteria": ["c1"], "estimation": "S"}'
        result = parse_llm_json(raw, PMSpec)
        assert result is not None
        assert result.estimation == "S"
        assert result.user_stories == ["s1"]

    def test_json_wrapped_in_text(self):
        raw = 'Here is the analysis:\n```json\n{"detailed_description": "d", "user_stories": [], "acceptance_criteria": [], "estimation": "L"}\n```'
        result = parse_llm_json(raw, PMSpec)
        assert result is not None
        assert result.estimation == "L"

    def test_invalid_json(self):
        raw = "This is not JSON at all"
        result = parse_llm_json(raw, PMSpec)
        assert result is None

    def test_schema_with_missing_optional_fields(self):
        raw = '{"architecture": "microservices"}'
        result = parse_llm_json(raw, ArchitectureDesign)
        assert result is not None
        assert result.architecture == "microservices"
        assert result.tech_stack == []

    def test_review_report_validation(self):
        raw = '{"overall_score": 85, "issues": [{"severity": "low", "description": "x"}], "suggestions": ["add tests"], "approved": true}'
        result = parse_llm_json(raw, ReviewReport)
        assert result is not None
        assert result.overall_score == 85
        assert result.approved is True
        assert len(result.issues) == 1

    def test_test_report_validation(self):
        raw = '{"test_cases": [{"id": "TC-1", "name": "test"}], "test_results": [{"case_id": "TC-1", "status": "pass"}], "coverage": "80%", "summary": "ok"}'
        result = parse_llm_json(raw, QATestReport)
        assert result is not None
        assert len(result.test_cases) == 1

    def test_ux_design_validation(self):
        raw = '{"information_architecture": {"pages": ["home"]}, "user_flows": [], "wireframes": [], "interaction_patterns": ["drag"], "design_system": null}'
        result = parse_llm_json(raw, UXDesign)
        assert result is not None
        assert result.interaction_patterns == ["drag"]

    def test_malformed_json_returns_none(self):
        raw = '{"architecture": "test", "tech_stack": [unclosed'
        result = parse_llm_json(raw, ArchitectureDesign)
        assert result is None
