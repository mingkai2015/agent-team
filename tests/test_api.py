"""Integration tests for the Agent Team API endpoints."""

import pytest


class TestHealthAndMeta:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "timestamp" in body

    def test_phases(self, client):
        resp = client.get("/phases")
        assert resp.status_code == 200
        body = resp.json()
        assert "phase_order" in body
        assert "gates" in body
        assert len(body["phase_order"]) == 7
        assert "requirement" in body["gates"]
        assert "deployment" in body["gates"]

    def test_skills(self, client):
        resp = client.get("/skills")
        assert resp.status_code == 200

    def test_evaluation_summary_empty(self, client):
        resp = client.get("/evaluation")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_tasks"] == 0

    def test_metrics(self, client):
        resp = client.get("/observability/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert "total_requests" in body
        assert "success_rate" in body


class TestTaskWorkflow:
    def test_create_requirement_and_list(self, client, sample_requirement):
        resp = client.post("/requirements", json=sample_requirement)
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "PENDING_APPROVAL"
        assert "task_id" in body
        task_id = body["task_id"]

        resp = client.get("/tasks")
        assert resp.status_code == 200
        tasks = resp.json()
        assert any(t["id"] == task_id for t in tasks)

    def test_get_task(self, client, sample_requirement):
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]

        resp = client.get(f"/tasks/{task_id}")
        assert resp.status_code == 200
        task = resp.json()
        assert task["id"] == task_id
        assert task["state"] == "PENDING_APPROVAL"
        assert task["artifacts"]["current_gate"] == "requirement"

    def test_get_task_not_found(self, client):
        resp = client.get("/tasks/nonexistent-id")
        assert resp.status_code == 404

    def test_approve_advances_to_architecture(self, client, sample_requirement):
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]

        resp = client.post(
            f"/tasks/{task_id}/approve",
            json={"approver": "admin", "decision": "approve", "comment": "OK"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "PENDING_APPROVAL"
        assert "架构" in body["message"]

        task = client.get(f"/tasks/{task_id}").json()
        assert "architecture" in task["artifacts"]
        assert task["artifacts"]["current_gate"] == "architecture"

    def test_reject_task(self, client, sample_requirement):
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]

        resp = client.post(
            f"/tasks/{task_id}/approve",
            json={"approver": "admin", "decision": "reject", "comment": "Need changes"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "REJECTED"
        assert "驳回" in body["message"]

    def test_approve_not_pending(self, client, sample_requirement):
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]

        client.post(
            f"/tasks/{task_id}/approve",
            json={"approver": "admin", "decision": "reject"},
        )

        resp = client.post(
            f"/tasks/{task_id}/approve",
            json={"approver": "admin", "decision": "approve"},
        )
        assert resp.status_code == 400

    def test_full_workflow_to_completion(self, client, sample_requirement):
        """Walk through all 7 phases and verify the task reaches COMPLETED."""
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]

        expected_phases = [
            "architecture", "ux_design", "implementation",
            "review", "testing", "deployment",
        ]

        for phase in expected_phases:
            resp = client.post(
                f"/tasks/{task_id}/approve",
                json={"approver": "admin", "decision": "approve", "comment": f"approve {phase}"},
            )
            assert resp.status_code == 200, f"Failed at phase before {phase}"

        final_resp = client.post(
            f"/tasks/{task_id}/approve",
            json={"approver": "admin", "decision": "approve", "comment": "final deploy approve"},
        )
        assert final_resp.status_code == 200
        body = final_resp.json()
        assert body["state"] == "COMPLETED"
        assert "完成" in body["message"]

        task = client.get(f"/tasks/{task_id}").json()
        assert task["state"] == "COMPLETED"
        assert len(task["approvals"]) == 7
        assert task["artifacts"]["current_gate"] is None

        eval_resp = client.get(f"/evaluation/{task_id}")
        assert eval_resp.status_code == 200
        ev = eval_resp.json()
        assert ev["grade"] in ("A", "B", "C", "D", "F")


class TestArtifactEndpoints:
    def _create_and_advance(self, client, sample_requirement, approvals: int):
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]
        for _ in range(approvals):
            client.post(
                f"/tasks/{task_id}/approve",
                json={"approver": "admin", "decision": "approve"},
            )
        return task_id

    def test_spec_endpoint(self, client, sample_requirement):
        task_id = self._create_and_advance(client, sample_requirement, 0)
        resp = client.get(f"/tasks/{task_id}/spec")
        assert resp.status_code == 200
        assert "title" in resp.json()

    def test_architecture_endpoint(self, client, sample_requirement):
        task_id = self._create_and_advance(client, sample_requirement, 1)
        resp = client.get(f"/tasks/{task_id}/architecture")
        assert resp.status_code == 200
        assert "tech_stack" in resp.json()

    def test_implementation_endpoint(self, client, sample_requirement):
        task_id = self._create_and_advance(client, sample_requirement, 3)
        resp = client.get(f"/tasks/{task_id}/implementation")
        assert resp.status_code == 200

    def test_review_endpoint(self, client, sample_requirement):
        task_id = self._create_and_advance(client, sample_requirement, 4)
        resp = client.get(f"/tasks/{task_id}/review")
        assert resp.status_code == 200

    def test_test_report_endpoint(self, client, sample_requirement):
        task_id = self._create_and_advance(client, sample_requirement, 5)
        resp = client.get(f"/tasks/{task_id}/test-report")
        assert resp.status_code == 200

    def test_deployment_endpoint(self, client, sample_requirement):
        task_id = self._create_and_advance(client, sample_requirement, 6)
        resp = client.get(f"/tasks/{task_id}/deployment")
        assert resp.status_code == 200
