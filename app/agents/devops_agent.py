import os
import json
import subprocess
from typing import Dict, Any, List
from datetime import datetime
from app.agents.llm_client import llm_client


DEVOPS_AGENT_SYSTEM_PROMPT = """
你是一个资深 DevOps 工程师，负责 CI/CD 流水线和部署自动化。

技术栈：
- 前端：React + TypeScript + Vite
- 后端：SpringBoot 3.x + Java 17 + Maven
- 数据库：PostgreSQL

你的职责：
1. 设计 CI/CD 流水线（GitLab CI）
2. 编写 Docker 配置（前端 + 后端）
3. 编写 docker-compose.yml
4. 部署到本地 Docker

输出必须为有效的 JSON 格式。
"""


class DevOpsAgent:
    def __init__(self):
        self.name = "DevOps Agent"
        self.llm = llm_client

    def deploy(
        self, spec: Dict[str, Any], implementation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate deployment configuration and deploy to local Docker"""
        code = implementation.get("code", [])

        result = self._fallback_deploy(spec, code)

        # Write code to local files
        self._write_code_to_disk(code, spec.get("title", "app"))

        # Build and deploy to local Docker
        deployment_result = self._deploy_to_docker(spec, code)

        result.update(deployment_result)
        return result

    def _write_code_to_disk(
        self, code: List[Dict[str, Any]], project_name: str
    ) -> None:
        """Write generated code to local disk"""
        project_name = project_name.replace(" ", "-").lower()
        workspace = f"/tmp/{project_name}"

        os.makedirs(workspace, exist_ok=True)

        for file in code:
            file_path = os.path.join(workspace, file.get("path", ""))
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file.get("content", ""))

        print(f"Code written to: {workspace}")

    def _deploy_to_docker(
        self, spec: Dict[str, Any], code: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build and deploy to local Docker"""
        project_name = spec.get("title", "app").replace(" ", "-").lower()
        workspace = f"/tmp/{project_name}"

        docker_compose = f"""version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/{project_name}
      - SPRING_DATASOURCE_USERNAME=postgres
      - SPRING_DATASOURCE_PASSWORD=postgres
    depends_on:
      - postgres
    networks:
      - app-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - app-network

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: {project_name}
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  postgres-data:
"""

        # Write docker-compose.yml
        compose_path = os.path.join(workspace, "docker-compose.yml")
        with open(compose_path, "w") as f:
            f.write(docker_compose)

        # Create backend Dockerfile
        backend_dockerfile = """FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
"""

        backend_dockerfile_path = os.path.join(workspace, "backend", "Dockerfile")
        os.makedirs(os.path.dirname(backend_dockerfile_path), exist_ok=True)
        with open(backend_dockerfile_path, "w") as f:
            f.write(backend_dockerfile)

        # Create frontend Dockerfile
        frontend_dockerfile = """FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""

        frontend_dockerfile_path = os.path.join(workspace, "frontend", "Dockerfile")
        os.makedirs(os.path.dirname(frontend_dockerfile_path), exist_ok=True)
        with open(frontend_dockerfile_path, "w") as f:
            f.write(frontend_dockerfile)

        # Create nginx config for frontend
        nginx_config = """server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    location /api {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
"""

        nginx_path = os.path.join(workspace, "frontend", "nginx.conf")
        os.makedirs(os.path.dirname(nginx_path), exist_ok=True)
        with open(nginx_path, "w") as f:
            f.write(nginx_config)

        # Build and run docker-compose
        try:
            # Stop existing containers
            subprocess.run(
                ["docker", "compose", "-f", compose_path, "down", "-v"],
                cwd=workspace,
                capture_output=True,
                timeout=60,
            )

            # Build and start containers
            result = subprocess.run(
                ["docker", "compose", "-f", compose_path, "up", "-d", "--build"],
                cwd=workspace,
                capture_output=True,
                timeout=600,
            )

            print(f"Docker build output: {result.stdout.decode()}")
            print(f"Docker build errors: {result.stderr.decode()}")

            return {
                "deployment_status": "success",
                "deployment_url": "http://localhost:3000",
                "backend_url": "http://localhost:8080",
                "workspace": workspace,
                "docker_compose_path": compose_path,
            }
        except Exception as e:
            print(f"Docker deployment failed: {e}")
            return {
                "deployment_status": "failed",
                "error": str(e),
                "workspace": workspace,
            }

    def _parse_json_response(self, response: str) -> Any:
        import re

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return None

    def _fallback_deploy(
        self, spec: Dict[str, Any], code: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return {
            "dockerfile_backend": """FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
""",
            "dockerfile_frontend": """FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
""",
            "docker_compose": """version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8080:8080"
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
  postgres:
    image: postgres:15
""",
            "ci_pipeline": """.gitlab-ci.yml:
stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - cd backend && mvn package
    - cd frontend && npm install && npm run build

deploy:
  stage: deploy
  script:
    - docker-compose up -d
  only:
    - main
""",
            "deployment_steps": [
                "1. 写入代码到本地目录",
                "2. 创建 Docker 配置文件",
                "3. 执行 docker-compose build",
                "4. 执行 docker-compose up -d",
                "5. 检查容器运行状态",
            ],
            "health_check": {
                "frontend": "http://localhost:3000",
                "backend": "http://localhost:8080/actuator/health",
            },
            "deployed_at": datetime.now().isoformat(),
            "status": "generated",
        }


devops_agent = DevOpsAgent()
