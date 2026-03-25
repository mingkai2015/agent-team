import os
import urllib.parse
import subprocess
import base64
from typing import Dict, Any, Optional, List


class GitLabClient:
    """
    GitLab API client (Mock mode for POC)
    """

    def __init__(self):
        self.mode = os.getenv("GITLAB_MODE", "mock")
        self.base_url = os.getenv("GITLAB_URL", "https://gitlab.com")
        self.token = os.getenv("GITLAB_TOKEN", "")
        self.project_id = os.getenv("GITLAB_PROJECT_ID", "")
        self.gitlab_repo_url = os.getenv("GITLAB_REPO_URL", "")

    def _get_project_path(self) -> str:
        """URL encode project path"""
        return urllib.parse.quote(self.project_id, safe="")

    def create_issue(
        self, title: str, description: str, labels: list = None
    ) -> Dict[str, Any]:
        """创建 GitLab Issue (Mock)"""
        if self.mode == "mock":
            return {
                "id": f"mock-issue-{hash(title) % 10000}",
                "iid": hash(title) % 10000,
                "title": title,
                "description": description,
                "labels": labels or [],
                "state": "opened",
                "web_url": f"{self.base_url}/-/issues/{hash(title) % 10000}",
                "created_at": "2026-03-24T00:00:00Z",
            }

        import httpx

        headers = {"PRIVATE-TOKEN": self.token}
        data = {
            "title": title,
            "description": description,
            "labels": ",".join(labels) if labels else "",
        }
        response = httpx.post(
            f"{self.base_url}/api/v4/projects/{self._get_project_path()}/issues",
            headers=headers,
            json=data,
            timeout=30.0,
        )
        return response.json()

    def create_mr(
        self, source_branch: str, target_branch: str, title: str, description: str
    ) -> Dict[str, Any]:
        """创建 Merge Request (Mock)"""
        if self.mode == "mock":
            return {
                "id": f"mock-mr-{hash(source_branch) % 10000}",
                "iid": hash(source_branch) % 10000,
                "title": title,
                "description": description,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "state": "open",
                "web_url": f"{self.base_url}/-/merge_requests/{hash(source_branch) % 10000}",
                "created_at": "2026-03-24T00:00:00Z",
            }

        import httpx

        headers = {"PRIVATE-TOKEN": self.token}
        data = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
        }
        response = httpx.post(
            f"{self.base_url}/api/v4/projects/{self._get_project_path()}/merge_requests",
            headers=headers,
            json=data,
            timeout=30.0,
        )
        return response.json()

    def update_issue(
        self, issue_iid: str, state: str = None, labels: list = None
    ) -> Dict[str, Any]:
        """更新 Issue (Mock)"""
        if self.mode == "mock":
            return {
                "iid": issue_iid,
                "state": state or "opened",
                "labels": labels or [],
            }

        import httpx

        headers = {"PRIVATE-TOKEN": self.token}
        data = {}
        if state:
            data["state_event"] = "close" if state == "closed" else "reopen"
        if labels:
            data["labels"] = ",".join(labels)

        response = httpx.put(
            f"{self.base_url}/api/v4/projects/{self._get_project_path()}/issues/{issue_iid}",
            headers=headers,
            json=data,
            timeout=30.0,
        )
        return response.json()

    def create_branch(self, branch_name: str, ref: str = "main") -> Dict[str, Any]:
        """创建分支 (Mock)"""
        if self.mode == "mock":
            return {
                "name": branch_name,
                "commit": {"id": "mock-commit-sha"},
                "protected": False,
            }

        import httpx

        headers = {"PRIVATE-TOKEN": self.token}
        data = {"branch": branch_name, "ref": ref}
        response = httpx.post(
            f"{self.base_url}/api/v4/projects/{self._get_project_path()}/repository/branches",
            headers=headers,
            json=data,
            timeout=30.0,
        )
        return response.json()

    def push_code(
        self, code: List[Dict[str, Any]], project_name: str, branch: str = "main"
    ) -> Dict[str, Any]:
        """Push code to GitLab repository"""
        if self.mode == "mock":
            return {
                "status": "mock",
                "project_name": project_name,
                "branch": branch,
                "files_pushed": len(code),
                "web_url": f"{self.base_url}/{self.project_id}/-/tree/{branch}",
            }

        if not self.gitlab_repo_url or not self.token:
            return {
                "status": "error",
                "message": "GitLab repo URL or token not configured",
            }

        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            # Clone repository
            repo_url_with_token = self.gitlab_repo_url.replace(
                "https://", f"https://oauth2:{self.token}@"
            )
            subprocess.run(
                ["git", "clone", repo_url_with_token, temp_dir],
                check=True,
                capture_output=True,
            )

            # Configure git user
            subprocess.run(
                ["git", "config", "user.email", "agent@localhost"],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "AI Agent"],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )

            # Create branch
            subprocess.run(
                ["git", "checkout", "-b", branch],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )

            # Write files
            for file in code:
                file_path = os.path.join(temp_dir, file.get("path", ""))
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file.get("content", ""))

            # Commit and push
            subprocess.run(
                ["git", "add", "."], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"feat: Initial implementation of {project_name}",
                ],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "push", "-u", "origin", branch],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )

            return {
                "status": "success",
                "project_name": project_name,
                "branch": branch,
                "files_pushed": len(code),
                "web_url": f"{self.gitlab_repo_url}/-/tree/{branch}",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


gitlab_client = GitLabClient()
