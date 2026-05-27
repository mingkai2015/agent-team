import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from app.agents.llm_client import LLMClient

logger = logging.getLogger(__name__)


DEV_AGENT_SYSTEM_PROMPT = """
You are a senior software engineer. Implement feature code based on the requirement spec.

Tech stack requirements:
- Frontend: React + TypeScript + Vite
- Backend: Spring Boot 3.x + Java 17 + Maven
- Database: PostgreSQL

Workflow:
1. Understand the requirement spec
2. Produce a technical implementation plan (explicit tech stack)
3. Implement backend code (Controller, Service, Repository, Entity, DTO)
4. Implement frontend code (React components, API calls)
5. Generate unit tests

Output format requirements:
- Implementation plan: JSON with architecture, tech_stack, api_design, data_model
- Code output: JSON array; each item includes path, content, language (java/typescript/javascript)
"""


class DevAgent:
    """
    Dev Agent with Spec Kit workflow integration
    """

    def __init__(self):
        self.name = "Dev Agent"
        self.llm = LLMClient()
        self.workspace = "/workspace"

    def implement(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Spec Kit workflow: specify -> plan -> tasks -> implement
        """
        results = {
            "plan": self._generate_plan(spec),
            "tasks": self._generate_tasks(spec),
            "code": self._generate_code(spec),
        }
        return results

    def _generate_plan(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical implementation plan"""
        title = spec.get("title", "")
        description = spec.get("detailed_description", "")

        prompt = f"""
As the technical lead, create a technical implementation plan for the following requirement:

Requirement: {title}
Details: {description}

Return a JSON plan:
{{
  "architecture": "Architecture description",
  "tech_stack": ["Tech stack items"],
  "api_design": ["API design notes"],
  "data_model": ["Data model notes"],
  "milestones": ["Milestone 1", "Milestone 2"]
}}
"""
        try:
            response = self.llm.chat(DEV_AGENT_SYSTEM_PROMPT, prompt)
            plan = self._parse_json_response(response)
            if plan:
                return plan
        except:
            pass

        return self._fallback_plan(spec)

    def _generate_tasks(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate task list (speckit.tasks equivalent)"""
        title = spec.get("title", "")

        prompt = f"""
Generate a task list for the requirement "{title}":

Return JSON:
[
  {{"id": "task-1", "description": "Task description", "phase": "setup", "status": "pending"}},
  {{"id": "task-2", "description": "Task description", "phase": "implementation", "status": "pending"}},
  {{"id": "task-3", "description": "Task description", "phase": "testing", "status": "pending"}}
]
"""
        try:
            response = self.llm.chat(DEV_AGENT_SYSTEM_PROMPT, prompt)
            tasks = self._parse_json_response(response, list_mode=True)
            if tasks and isinstance(tasks, list):
                return tasks
        except Exception as e:
            logger.error("Dev Agent tasks generation failed: %s", e)

        return self._fallback_tasks(spec)

    def _generate_code(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate code implementation"""
        title = spec.get("title", "")

        prompt = f"""
Generate an example code structure for the requirement "{title}".

Return JSON:
[
  {{"path": "main.py", "content": "# code"}},
  {{"path": "models.py", "content": "# code"}},
  {{"path": "test_main.py", "content": "# tests"}}
]
"""
        try:
            response = self.llm.chat(DEV_AGENT_SYSTEM_PROMPT, prompt)
            code = self._parse_json_response(response, list_mode=True)
            if code and isinstance(code, list):
                return code
        except Exception as e:
            logger.error("Dev Agent code generation failed: %s", e)

        return self._fallback_code(spec)

    def _parse_json_response(self, response: str, list_mode: bool = False) -> Any:
        import re
        from app.schemas import parse_llm_json, DevPlan

        if not list_mode:
            parsed = parse_llm_json(response, DevPlan)
            return parsed.model_dump() if parsed else None

        json_match = re.search(r"\[[\s\S]*\]", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except Exception:
                pass
        return None

    def _fallback_plan(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "architecture": "Decoupled frontend/backend architecture: React frontend + Spring Boot REST API backend",
            "tech_stack": [
                "React 18",
                "TypeScript",
                "Vite",
                "SpringBoot 3.2",
                "Java 17",
                "Maven",
                "PostgreSQL",
            ],
            "api_design": [
                "GET /api/items - list items",
                "POST /api/items - create item",
                "PUT /api/items/{id} - update item",
                "DELETE /api/items/{id} - delete item",
            ],
            "data_model": ["Item: id, name, quantity, createdAt, updatedAt"],
            "milestones": ["Backend setup", "Frontend setup", "API integration", "Testing & deployment"],
        }

    def _fallback_tasks(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "id": "task-1",
                "description": "Create project structure",
                "phase": "setup",
                "status": "completed",
            },
            {
                "id": "task-2",
                "description": "Implement data model",
                "phase": "implementation",
                "status": "completed",
            },
            {
                "id": "task-3",
                "description": "Implement API endpoints",
                "phase": "implementation",
                "status": "pending",
            },
            {
                "id": "task-4",
                "description": "Write unit tests",
                "phase": "testing",
                "status": "pending",
            },
            {
                "id": "task-5",
                "description": "Deployment verification",
                "phase": "deploy",
                "status": "pending",
            },
        ]

    def _fallback_code(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "path": "backend/pom.xml",
                "language": "xml",
                "content": """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
        <relativePath/>
    </parent>
    
    <groupId>com.example</groupId>
    <artifactId>inventory-system</artifactId>
    <version>1.0.0</version>
    <name>inventory-system</name>
    
    <properties>
        <java.version>17</java.version>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>""",
            },
            {
                "path": "backend/src/main/java/com/example/inventory/InventoryApplication.java",
                "language": "java",
                "content": """package com.example.inventory;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class InventoryApplication {
    public static void main(String[] args) {
        SpringApplication.run(InventoryApplication.class, args);
    }
}""",
            },
            {
                "path": "backend/src/main/java/com/example/inventory/entity/Item.java",
                "language": "java",
                "content": """package com.example.inventory.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "items")
public class Item {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false)
    private String name;
    
    private Integer quantity;
    
    @Column(name = "created_at")
    private LocalDateTime createdAt;
    
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
    
    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }
    
    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
    
    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
}""",
            },
            {
                "path": "backend/src/main/java/com/example/inventory/repository/ItemRepository.java",
                "language": "java",
                "content": """package com.example.inventory.repository;

import com.example.inventory.entity.Item;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ItemRepository extends JpaRepository<Item, Long> {
}""",
            },
            {
                "path": "backend/src/main/java/com/example/inventory/service/ItemService.java",
                "language": "java",
                "content": """package com.example.inventory.service;

import com.example.inventory.entity.Item;
import com.example.inventory.repository.ItemRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class ItemService {
    
    @Autowired
    private ItemRepository itemRepository;
    
    public List<Item> getAllItems() {
        return itemRepository.findAll();
    }
    
    public Item createItem(Item item) {
        return itemRepository.save(item);
    }
    
    public Item updateItem(Long id, Item item) {
        Item existing = itemRepository.findById(id)
            .orElseThrow(() -> new RuntimeException("Item not found"));
        existing.setName(item.getName());
        existing.setQuantity(item.getQuantity());
        return itemRepository.save(existing);
    }
    
    public void deleteItem(Long id) {
        itemRepository.deleteById(id);
    }
}""",
            },
            {
                "path": "backend/src/main/java/com/example/inventory/controller/ItemController.java",
                "language": "java",
                "content": """package com.example.inventory.controller;

import com.example.inventory.entity.Item;
import com.example.inventory.service.ItemService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/items")
@CrossOrigin(origins = "*")
public class ItemController {
    
    @Autowired
    private ItemService itemService;
    
    @GetMapping
    public List<Item> getAllItems() {
        return itemService.getAllItems();
    }
    
    @PostMapping
    public Item createItem(@RequestBody Item item) {
        return itemService.createItem(item);
    }
    
    @PutMapping("/{id}")
    public ResponseEntity<Item> updateItem(@PathVariable Long id, @RequestBody Item item) {
        return ResponseEntity.ok(itemService.updateItem(id, item));
    }
    
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteItem(@PathVariable Long id) {
        itemService.deleteItem(id);
        return ResponseEntity.ok().build();
    }
}""",
            },
            {
                "path": "backend/src/main/resources/application.properties",
                "language": "properties",
                "content": """spring.application.name=inventory-system
server.port=8080

spring.datasource.url=jdbc:postgresql://localhost:5432/inventory
spring.datasource.username=postgres
spring.datasource.password=postgres

spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=true""",
            },
            {
                "path": "frontend/package.json",
                "language": "json",
                "content": """{
  "name": "inventory-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}""",
            },
            {
                "path": "frontend/vite.config.ts",
                "language": "typescript",
                "content": """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8080'
    }
  }
})""",
            },
            {
                "path": "frontend/src/main.tsx",
                "language": "typescript",
                "content": """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)""",
            },
            {
                "path": "frontend/src/App.tsx",
                "language": "typescript",
                "content": """import { useState, useEffect } from 'react'
import axios from 'axios'

interface Item {
  id: number
  name: string
  quantity: number
}

function App() {
  const [items, setItems] = useState<Item[]>([])
  const [newItem, setNewItem] = useState({ name: '', quantity: 0 })

  useEffect(() => {
    fetchItems()
  }, [])

  const fetchItems = async () => {
    const res = await axios.get('http://localhost:8080/api/items')
    setItems(res.data)
  }

  const createItem = async () => {
    await axios.post('http://localhost:8080/api/items', newItem)
    setNewItem({ name: '', quantity: 0 })
    fetchItems()
  }

  const deleteItem = async (id: number) => {
    await axios.delete(`http://localhost:8080/api/items/${id}`)
    fetchItems()
  }

  return (
    <div>
      <h1>Inventory System</h1>
      <div>
        <input 
          placeholder="Name" 
          value={newItem.name}
          onChange={e => setNewItem({...newItem, name: e.target.value})}
        />
        <input 
          type="number"
          placeholder="Quantity"
          value={newItem.quantity}
          onChange={e => setNewItem({...newItem, quantity: parseInt(e.target.value)})}
        />
        <button onClick={createItem}>Add</button>
      </div>
      <ul>
        {items.map(item => (
          <li key={item.id}>
            {item.name} - {item.quantity}
            <button onClick={() => deleteItem(item.id)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default App""",
            },
            {
                "path": "frontend/src/index.css",
                "language": "css",
                "content": """body {
  font-family: Arial, sans-serif;
  margin: 20px;
  background: #f5f5f5;
}

h1 {
  color: #333;
}

div {
  margin: 10px 0;
}

input {
  padding: 8px;
  margin: 5px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

button {
  padding: 8px 16px;
  margin: 5px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background: #0056b3;
}

ul {
  list-style: none;
  padding: 0;
}

li {
  background: white;
  padding: 10px;
  margin: 5px 0;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}""",
            },
            {
                "path": "frontend/index.html",
                "language": "html",
                "content": """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Inventory System</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>""",
            },
            {
                "path": "frontend/tsconfig.json",
                "language": "json",
                "content": """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}""",
            },
        ]

    def _fallback_impl(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback implementation when LLM fails"""
        return {
            "plan": self._fallback_plan(spec),
            "tasks": self._fallback_tasks(spec),
            "code": self._fallback_code(spec),
        }


dev_agent = DevAgent()
