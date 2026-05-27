import os
import sys
from unittest.mock import MagicMock, patch

os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["GITLAB_MODE"] = "mock"
os.environ["ANTHROPIC_BASE_URL"] = ""
os.environ["ANTHROPIC_AUTH_TOKEN"] = ""
os.environ["API_KEY"] = ""

_store: dict[str, dict[str, str]] = {}


class FakeRedis:
    """In-memory Redis stand-in for testing."""

    def hset(self, key, field, value):
        _store.setdefault(key, {})[field] = value

    def hget(self, key, field):
        return _store.get(key, {}).get(field)

    def hkeys(self, key):
        return list(_store.get(key, {}).keys())

    def hgetall(self, key):
        return _store.get(key, {})

    def hdel(self, key, field):
        return _store.get(key, {}).pop(field, None) is not None

    def ping(self):
        return True


_fake_redis_instance = FakeRedis()


class _FakeRedisModule:
    @staticmethod
    def from_url(*args, **kwargs):
        return _fake_redis_instance

    Redis = MagicMock
    StrictRedis = MagicMock


sys.modules.setdefault("redis", _FakeRedisModule())

import pytest
from fastapi.testclient import TestClient


def _fake_subprocess_run(*args, **kwargs):
    result = MagicMock()
    result.returncode = 0
    result.stdout = b"mock output"
    result.stderr = b""
    return result


@pytest.fixture(autouse=True)
def _clear_store():
    _store.clear()
    from app.database import db
    db.redis = _fake_redis_instance
    from app.observability import observability
    observability.redis = _fake_redis_instance
    observability.traces = {}
    observability.metrics = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "total_duration_ms": 0,
        "agent_stats": {},
        "phase_durations": {},
    }
    from app.evaluation import evaluation
    evaluation.evaluations = []
    evaluation.task_metrics = {}
    from app.agents.llm_client import llm_client
    llm_client.max_retries = 1
    llm_client.retry_delay = 0.0

    with patch("subprocess.run", side_effect=_fake_subprocess_run), \
         patch("app.agents.devops_agent.subprocess.run", side_effect=_fake_subprocess_run), \
         patch("app.agents.gitlab_client.subprocess.run", side_effect=_fake_subprocess_run):
        yield


@pytest.fixture
def client():
    from langgraph.checkpoint.memory import MemorySaver
    from app.workflow.graph import compile_workflow
    import app.main as main_mod

    main_mod.workflow = compile_workflow(checkpointer=MemorySaver())

    with patch("subprocess.run", side_effect=_fake_subprocess_run), \
         patch("app.agents.devops_agent.subprocess.run", side_effect=_fake_subprocess_run), \
         patch("app.agents.gitlab_client.subprocess.run", side_effect=_fake_subprocess_run):
        with TestClient(main_mod.app) as c:
            yield c


@pytest.fixture
def sample_project(client):
    resp = client.post("/projects", json={
        "name": "Test Project",
        "description": "Project used for testing",
        "gitlab_mode": "mock",
    })
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
def sample_requirement(sample_project):
    return {
        "project_id": sample_project["id"],
        "title": "Test Order System",
        "description": "Build a simple order management system that supports creating and querying orders",
        "priority": "P1",
    }
