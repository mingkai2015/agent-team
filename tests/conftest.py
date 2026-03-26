import os
import sys
import subprocess
from unittest.mock import MagicMock, patch

os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["GITLAB_MODE"] = "mock"
os.environ["ANTHROPIC_BASE_URL"] = ""
os.environ["ANTHROPIC_AUTH_TOKEN"] = ""

_store: dict[str, dict[str, str]] = {}


class FakeRedis:
    """In-memory Redis stand-in that implements the hash commands we use."""

    def hset(self, key, field, value):
        _store.setdefault(key, {})[field] = value

    def hget(self, key, field):
        return _store.get(key, {}).get(field)

    def hkeys(self, key):
        return list(_store.get(key, {}).keys())

    def hgetall(self, key):
        return _store.get(key, {})

    def ping(self):
        return True


_fake_redis_instance = FakeRedis()


class _FakeRedisModule:
    """Drop-in for the `redis` package: from_url returns our fake."""

    @staticmethod
    def from_url(*args, **kwargs):
        return _fake_redis_instance

    Redis = MagicMock
    StrictRedis = MagicMock


sys.modules.setdefault("redis", _FakeRedisModule())

import pytest
from fastapi.testclient import TestClient


def _fake_subprocess_run(*args, **kwargs):
    """Prevent real Docker/git calls during tests."""
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

    with patch("subprocess.run", side_effect=_fake_subprocess_run), \
         patch("app.agents.devops_agent.subprocess.run", side_effect=_fake_subprocess_run), \
         patch("app.agents.gitlab_client.subprocess.run", side_effect=_fake_subprocess_run):
        yield


@pytest.fixture
def client():
    from app.main import app
    with patch("subprocess.run", side_effect=_fake_subprocess_run), \
         patch("app.agents.devops_agent.subprocess.run", side_effect=_fake_subprocess_run), \
         patch("app.agents.gitlab_client.subprocess.run", side_effect=_fake_subprocess_run):
        with TestClient(app) as c:
            yield c


@pytest.fixture
def sample_requirement():
    return {
        "title": "测试订单系统",
        "description": "开发一个简单的订单管理系统，支持创建和查询订单",
        "priority": "P1",
    }
