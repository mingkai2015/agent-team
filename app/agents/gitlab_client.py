import os
import logging
import urllib.parse
import subprocess
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class GitLabAPIError(Exception):
    """Raised when a GitLab API call returns a non-2xx status."""

    def __init__(self, status_code: int, body: str, url: str):
        self.status_code = status_code
        self.body = body
        self.url = url
        super().__init__(f"GitLab API {status_code} at {url}: {body[:200]}")


class GitLabClient:
    """
    GitLab API client (Mock mode for POC)
    """

    def __init__(self, config: dict = None):
        if config:
            self.mode = config.get("gitlab_mode", "mock")
            self.base_url = config.get("gitlab_url", "https://gitlab.com")
            self.token = config.get("gitlab_token", "")
            self.project_id = config.get("gitlab_project_id", "")
            self.gitlab_repo_url = config.get("gitlab_repo_url", "")
            self.main_branch = config.get("main_branch", "main")
        else:
            self.mode = os.getenv("GITLAB_MODE", "mock")
            self.base_url = os.getenv("GITLAB_URL", "https://gitlab.com")
            self.token = os.getenv("GITLAB_TOKEN", "")
            self.project_id = os.getenv("GITLAB_PROJECT_ID", "")
            self.gitlab_repo_url = os.getenv("GITLAB_REPO_URL", "")
            self.main_branch = "main"

    def _check_response(self, response, url: str) -> Dict[str, Any]:
        if response.status_code >= 400:
            raise GitLabAPIError(response.status_code, response.text, url)
        return response.json()

    def _get_project_path(self) -> str:
        """URL encode project path"""
        return urllib.parse.quote(self.project_id, safe="")

    def create_issue(
        self, title: str, description: str, labels: list = None
    ) -> Dict[str, Any]:
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

        url = f"{self.base_url}/api/v4/projects/{self._get_project_path()}/issues"
        headers = {"PRIVATE-TOKEN": self.token}
        data = {
            "title": title,
            "description": description,
            "labels": ",".join(labels) if labels else "",
        }
        try:
            response = httpx.post(url, headers=headers, json=data, timeout=30.0)
            return self._check_response(response, url)
        except GitLabAPIError:
            raise
        except Exception as e:
            logger.error("GitLab create_issue failed: %s", e)
            return {"error": str(e), "title": title}

    def create_mr(
        self, source_branch: str, target_branch: str, title: str, description: str
    ) -> Dict[str, Any]:
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

        url = f"{self.base_url}/api/v4/projects/{self._get_project_path()}/merge_requests"
        headers = {"PRIVATE-TOKEN": self.token}
        data = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
        }
        try:
            response = httpx.post(url, headers=headers, json=data, timeout=30.0)
            return self._check_response(response, url)
        except GitLabAPIError:
            raise
        except Exception as e:
            logger.error("GitLab create_mr failed: %s", e)
            return {"error": str(e), "source_branch": source_branch}

    def update_issue(
        self, issue_iid: str, state: str = None, labels: list = None
    ) -> Dict[str, Any]:
        if self.mode == "mock":
            return {
                "iid": issue_iid,
                "state": state or "opened",
                "labels": labels or [],
            }

        import httpx

        url = f"{self.base_url}/api/v4/projects/{self._get_project_path()}/issues/{issue_iid}"
        headers = {"PRIVATE-TOKEN": self.token}
        data = {}
        if state:
            data["state_event"] = "close" if state == "closed" else "reopen"
        if labels:
            data["labels"] = ",".join(labels)

        try:
            response = httpx.put(url, headers=headers, json=data, timeout=30.0)
            return self._check_response(response, url)
        except GitLabAPIError:
            raise
        except Exception as e:
            logger.error("GitLab update_issue failed: %s", e)
            return {"error": str(e), "iid": issue_iid}

    def create_branch(self, branch_name: str, ref: str = "main") -> Dict[str, Any]:
        if self.mode == "mock":
            return {
                "name": branch_name,
                "commit": {"id": "mock-commit-sha"},
                "protected": False,
            }

        import httpx

        url = f"{self.base_url}/api/v4/projects/{self._get_project_path()}/repository/branches"
        headers = {"PRIVATE-TOKEN": self.token}
        data = {"branch": branch_name, "ref": ref}
        try:
            response = httpx.post(url, headers=headers, json=data, timeout=30.0)
            return self._check_response(response, url)
        except GitLabAPIError:
            raise
        except Exception as e:
            logger.error("GitLab create_branch failed: %s", e)
            return {"error": str(e), "branch": branch_name}

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
