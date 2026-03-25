import os
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum


class AgentPhase(str, Enum):
    PM = "pm"
    TL = "tl"
    DEV = "dev"
    REVIEWER = "reviewer"
    QA = "qa"
    DEVOPS = "devops"


class TraceEvent:
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str],
        agent: str,
        phase: str,
        event_type: str,
        status: str,
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.agent = agent
        self.phase = phase
        self.event_type = event_type
        self.status = status
        self.input_data = input_data
        self.output_data = output_data
        self.error = error
        self.duration_ms = duration_ms
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "agent": self.agent,
            "phase": self.phase,
            "event_type": self.event_type,
            "status": self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


class Observability:
    def __init__(self):
        import os
        import redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self._traces_key = "agent_team:traces"

        self.traces: Dict[str, List[Dict]] = {}
        self.metrics: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration_ms": 0,
            "agent_stats": {},
            "phase_durations": {},
        }

        self._load_traces_from_redis()

    def start_trace(self, task_id: str, phase: str) -> str:
        trace_id = f"trace-{task_id}-{int(time.time() * 1000)}"
        span_id = f"span-{uuid.uuid4().hex[:8]}"

        event = TraceEvent(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            agent="system",
            phase=phase,
            event_type="trace_start",
            status="started",
            input_data={"task_id": task_id},
        )

        self._add_event(task_id, event)
        return trace_id

    def record_agent_call(
        self,
        task_id: str,
        trace_id: str,
        agent: str,
        phase: str,
        input_data: Dict,
        output_data: Dict = None,
        error: str = None,
        duration_ms: int = None,
    ):
        span_id = f"span-{uuid.uuid4().hex[:8]}"

        event = TraceEvent(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=trace_id,
            agent=agent,
            phase=phase,
            event_type="agent_call",
            status="error" if error else "success",
            input_data=self._sanitize_data(input_data),
            output_data=self._sanitize_data(output_data) if output_data else None,
            error=error,
            duration_ms=duration_ms,
        )

        self._add_event(task_id, event)
        self._update_metrics(agent, phase, error, duration_ms)

    def _sanitize_data(self, data: Dict) -> Dict:
        """Remove sensitive data from traces"""
        if not data:
            return {}
        sanitized = {}
        for key, value in data.items():
            if key in ["token", "password", "secret", "key"]:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "..."
            else:
                sanitized[key] = value
        return sanitized

    def _load_traces_from_redis(self):
        try:
            data = self.redis.hgetall(self._traces_key)
            for task_id, trace_data in data.items():
                try:
                    self.traces[task_id] = json.loads(trace_data)
                except:
                    pass
        except Exception as e:
            print(f"Failed to load traces from Redis: {e}")

    def _save_traces_to_redis(self):
        try:
            for task_id, traces in self.traces.items():
                self.redis.hset(
                    self._traces_key, task_id, json.dumps(traces, default=str)
                )
        except Exception as e:
            print(f"Failed to save traces to Redis: {e}")

    def _add_event(self, task_id: str, event: TraceEvent):
        if task_id not in self.traces:
            self.traces[task_id] = []
        self.traces[task_id].append(event.to_dict())
        self._save_traces_to_redis()

    def _update_metrics(self, agent: str, phase: str, error: str, duration_ms: int):
        self.metrics["total_requests"] += 1
        if error:
            self.metrics["failed_requests"] += 1
        else:
            self.metrics["successful_requests"] += 1

        if duration_ms:
            self.metrics["total_duration_ms"] += duration_ms

            if phase not in self.metrics["phase_durations"]:
                self.metrics["phase_durations"][phase] = {
                    "count": 0,
                    "total_ms": 0,
                    "avg_ms": 0,
                }

            phase_stats = self.metrics["phase_durations"][phase]
            phase_stats["count"] += 1
            phase_stats["total_ms"] += duration_ms
            phase_stats["avg_ms"] = phase_stats["total_ms"] / phase_stats["count"]

        if agent not in self.metrics["agent_stats"]:
            self.metrics["agent_stats"][agent] = {"calls": 0, "errors": 0}

        agent_stats = self.metrics["agent_stats"][agent]
        agent_stats["calls"] += 1
        if error:
            agent_stats["errors"] += 1

    def get_trace(self, task_id: str) -> List[Dict]:
        return self.traces.get(task_id, [])

    def get_metrics(self) -> Dict:
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful_requests"]
                / max(1, self.metrics["total_requests"])
                * 100
            ),
            "avg_duration_ms": (
                self.metrics["total_duration_ms"]
                / max(1, self.metrics["total_requests"])
            ),
        }


observability = Observability()
