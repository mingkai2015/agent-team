import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict


class EvaluationMetrics:
    def __init__(self):
        self.evaluations: List[Dict] = []
        self.task_metrics: Dict[str, Dict] = {}

    def evaluate_task(
        self, task_id: str, artifacts: Dict, approvals: List[Dict]
    ) -> Dict:
        """Evaluate a completed task"""
        evaluation = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "scores": {},
            "total_score": 0,
            "grade": "",
        }

        if "spec" in artifacts:
            spec_score = self._evaluate_spec(artifacts["spec"])
            evaluation["scores"]["spec_quality"] = spec_score

        if "architecture" in artifacts:
            arch_score = self._evaluate_architecture(artifacts["architecture"])
            evaluation["scores"]["architecture_quality"] = arch_score

        if "implementation" in artifacts:
            impl_score = self._evaluate_implementation(artifacts["implementation"])
            evaluation["scores"]["implementation_quality"] = impl_score

        if "review" in artifacts:
            review_score = self._evaluate_review(artifacts["review"])
            evaluation["scores"]["review_quality"] = review_score

        if "testing" in artifacts:
            test_score = self._evaluate_test(artifacts["testing"])
            evaluation["scores"]["test_quality"] = test_score

        if "ux_design" in artifacts:
            ux_score = self._evaluate_ux_design(artifacts["ux_design"])
            evaluation["scores"]["ux_quality"] = ux_score

        if "deployment" in artifacts:
            deploy_score = self._evaluate_deployment(artifacts["deployment"])
            evaluation["scores"]["deployment_quality"] = deploy_score

        approval_score = self._evaluate_approvals(approvals)
        evaluation["scores"]["approval_completion"] = approval_score

        phase_score = self._evaluate_phases(artifacts.get("phases_completed", []))
        evaluation["scores"]["phase_completion"] = phase_score

        total = sum(evaluation["scores"].values()) / len(evaluation["scores"])
        evaluation["total_score"] = round(total, 1)

        if total >= 90:
            evaluation["grade"] = "A"
        elif total >= 80:
            evaluation["grade"] = "B"
        elif total >= 70:
            evaluation["grade"] = "C"
        elif total >= 60:
            evaluation["grade"] = "D"
        else:
            evaluation["grade"] = "F"

        self.evaluations.append(evaluation)
        self.task_metrics[task_id] = evaluation

        return evaluation

    def _evaluate_spec(self, spec: Dict) -> float:
        score = 70
        if spec.get("user_stories"):
            score += min(10, len(spec["user_stories"]) * 2)
        if spec.get("acceptance_criteria"):
            score += min(10, len(spec["acceptance_criteria"]) * 2)
        if spec.get("detailed_description"):
            score += 5
        return min(100, score)

    def _evaluate_architecture(self, arch: Dict) -> float:
        score = 70
        if arch.get("tech_stack"):
            score += min(10, len(arch["tech_stack"]) * 2)
        if arch.get("api_design"):
            score += 5
        if arch.get("data_model"):
            score += 5
        if arch.get("security"):
            score += 5
        if arch.get("risks"):
            score += 5
        return min(100, score)

    def _evaluate_implementation(self, impl: Dict) -> float:
        score = 60
        if impl.get("code"):
            score += min(15, len(impl["code"]) * 5)
        if impl.get("tasks"):
            score += min(10, len(impl["tasks"]) * 2)
        if impl.get("plan"):
            score += 10
        return min(100, score)

    def _evaluate_review(self, review: Dict) -> float:
        score = 70
        if review.get("overall_score"):
            score = review["overall_score"]
        if review.get("issues"):
            if not any(i.get("severity") == "high" for i in review["issues"]):
                score += 10
        return min(100, score)

    def _evaluate_test(self, test_report: Dict) -> float:
        score = 70
        if test_report.get("test_cases"):
            score += min(15, len(test_report["test_cases"]) * 3)
        if test_report.get("test_results"):
            passed = sum(
                1 for r in test_report["test_results"] if r.get("status") == "pass"
            )
            total = len(test_report["test_results"])
            if total > 0:
                score = min(100, (passed / total) * 50 + 50)
        return min(100, score)

    def _evaluate_ux_design(self, ux: Dict) -> float:
        score = 70
        if ux.get("information_architecture"):
            score += 5
        if ux.get("user_flows"):
            score += min(10, len(ux["user_flows"]) * 5)
        if ux.get("wireframes"):
            score += min(10, len(ux["wireframes"]) * 3)
        if ux.get("design_system"):
            score += 5
        return min(100, score)

    def _evaluate_deployment(self, deploy: Dict) -> float:
        score = 70
        if deploy.get("dockerfile") or deploy.get("dockerfile_backend"):
            score += 10
        if deploy.get("docker_compose"):
            score += 10
        if deploy.get("ci_pipeline"):
            score += 10
        return min(100, score)

    def _evaluate_approvals(self, approvals: List[Dict]) -> float:
        return min(100, len(approvals) * 15)

    def _evaluate_phases(self, phases: List[str]) -> float:
        return min(100, len(phases) * 20)

    def get_task_evaluation(self, task_id: str) -> Optional[Dict]:
        return self.task_metrics.get(task_id)

    def get_average_score(self) -> float:
        if not self.evaluations:
            return 0
        return sum(e["total_score"] for e in self.evaluations) / len(self.evaluations)

    def get_grade_distribution(self) -> Dict[str, int]:
        grades = defaultdict(int)
        for e in self.evaluations:
            grades[e["grade"]] += 1
        return dict(grades)


evaluation = EvaluationMetrics()
