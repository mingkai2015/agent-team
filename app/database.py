import os
import redis
import json
from typing import Optional, List
from datetime import datetime
from app.models import Task, TaskState


class Database:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self._tasks_key = "agent_team:tasks"
        self._requirements_key = "agent_team:requirements"

    def save_task(self, task: Task) -> Task:
        task.updated_at = datetime.now()
        self.redis.hset(
            self._tasks_key,
            task.id,
            json.dumps(task.model_dump(mode="json"), default=str),
        )
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        data = self.redis.hget(self._tasks_key, task_id)
        if data:
            return Task(**json.loads(data))
        return None

    def get_all_tasks(self) -> List[Task]:
        tasks = []
        for task_id in self.redis.hkeys(self._tasks_key):
            task = self.get_task(task_id)
            if task:
                tasks.append(task)
        return tasks

    def save_requirement(self, requirement: dict) -> dict:
        self.redis.hset(
            self._requirements_key,
            requirement["id"],
            json.dumps(requirement, default=str),
        )
        return requirement

    def get_requirement(self, req_id: str) -> Optional[dict]:
        data = self.redis.hget(self._requirements_key, req_id)
        if data:
            return json.loads(data)
        return None


db = Database()
