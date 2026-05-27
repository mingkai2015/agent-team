"""Integration tests for the Agent Team API with LangGraph workflow."""

import pytest


class TestHealthAndMeta:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("healthy", "degraded")
        assert "checks" in body

    def test_phases(self, client):
        resp = client.get("/phases")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["phase_order"]) == 7
        assert "requirement" in body["gates"]
        assert "deployment" in body["gates"]

    def test_skills(self, client):
        resp = client.get("/skills")
        assert resp.status_code == 200

    def test_evaluation_summary_empty(self, client):
        resp = client.get("/evaluation")
        assert resp.status_code == 200
        assert resp.json()["total_tasks"] == 0

    def test_metrics(self, client):
        resp = client.get("/observability/metrics")
        assert resp.status_code == 200
        assert "success_rate" in resp.json()

    def test_workflow_graph(self, client):
        resp = client.get("/workflow/graph")
        assert resp.status_code == 200
        body = resp.json()
        assert "mermaid" in body


class TestProjectCRUD:
    def test_create_and_list_project(self, client):
        resp = client.post("/projects", json={
            "name": "Project A", "description": "Test", "gitlab_mode": "mock",
        })
        assert resp.status_code == 200
        pid = resp.json()["id"]

        resp = client.get("/projects")
        assert any(p["id"] == pid for p in resp.json())

    def test_get_project(self, client, sample_project):
        resp = client.get(f"/projects/{sample_project['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Project"

    def test_delete_project(self, client, sample_project):
        resp = client.delete(f"/projects/{sample_project['id']}")
        assert resp.status_code == 200
        resp = client.get(f"/projects/{sample_project['id']}")
        assert resp.status_code == 404


class TestTaskWorkflow:
    def test_create_requirement(self, client, sample_requirement):
        resp = client.post("/requirements", json=sample_requirement)
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "PENDING_APPROVAL"
        assert "task_id" in body

    def test_get_task(self, client, sample_requirement):
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]
        resp = client.get(f"/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["state"] == "PENDING_APPROVAL"

    def test_task_not_found(self, client):
        resp = client.get("/tasks/nonexistent-id")
        assert resp.status_code == 404

    def test_approve_advances_to_architecture(self, client, sample_requirement):
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]

        resp = client.post(f"/tasks/{task_id}/approve", json={
            "approver": "admin", "decision": "approve", "comment": "OK",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "PENDING_APPROVAL"

        task = client.get(f"/tasks/{task_id}").json()
        assert "architecture" in task["artifacts"]

    def test_reject_task(self, client, sample_requirement):
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]

        resp = client.post(f"/tasks/{task_id}/approve", json={
            "approver": "admin", "decision": "reject", "comment": "Needs changes",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "rejected" in body["message"].lower() or "rework" in body["message"].lower()

    def test_full_workflow_to_completion(self, client, sample_requirement):
        """Walk through all phases to COMPLETED (6 approvals with merged design)."""
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]

        for i in range(20):
            resp = client.post(f"/tasks/{task_id}/approve", json={
                "approver": "admin", "decision": "approve", "comment": f"phase {i+1}",
            })
            if resp.status_code != 200:
                break
            body = resp.json()
            if body["state"] == "COMPLETED":
                break

        assert body["state"] == "COMPLETED"
        assert "completed" in body["message"].lower()

        task = client.get(f"/tasks/{task_id}").json()
        assert task["state"] == "COMPLETED"

        eval_resp = client.get(f"/evaluation/{task_id}")
        assert eval_resp.status_code == 200


class TestArtifactEndpoints:
    def _advance(self, client, sample_requirement, approvals: int):
        create_resp = client.post("/requirements", json=sample_requirement)
        task_id = create_resp.json()["task_id"]
        for _ in range(approvals):
            client.post(f"/tasks/{task_id}/approve", json={
                "approver": "admin", "decision": "approve",
            })
        return task_id

    def test_spec_endpoint(self, client, sample_requirement):
        task_id = self._advance(client, sample_requirement, 0)
        resp = client.get(f"/tasks/{task_id}/spec")
        assert resp.status_code == 200

    def test_architecture_endpoint(self, client, sample_requirement):
        task_id = self._advance(client, sample_requirement, 1)
        resp = client.get(f"/tasks/{task_id}/architecture")
        assert resp.status_code == 200

    def test_implementation_endpoint(self, client, sample_requirement):
        task_id = self._advance(client, sample_requirement, 3)
        resp = client.get(f"/tasks/{task_id}/implementation")
        assert resp.status_code == 200
