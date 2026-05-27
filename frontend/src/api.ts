const API_BASE = import.meta.env.VITE_API_URL || '';

export interface Project {
  id: string;
  name: string;
  description: string;
  gitlab_mode?: string;
  workflow_template?: string;
  created_at?: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  state: string;
  assignee?: string;
  current_phase?: string;
  current_gate?: string;
  priority?: string;
  project_id?: string;
  artifacts?: Record<string, unknown>;
  approvals?: Approval[];
  created_at?: string;
  updated_at?: string;
}

export interface Approval {
  approver: string;
  decision: string;
  comment: string;
  timestamp: string;
  gate?: string;
}

export interface HealthStatus {
  status: string;
  checks: Record<string, unknown>;
  timestamp: string;
}

export interface EvaluationSummary {
  total_tasks: number;
  average_score: number;
  grade_distribution: Record<string, number>;
}

export interface TaskEvaluation {
  total_score: number;
  grade: string;
  scores: Record<string, number>;
}

export interface WorkflowGraph {
  mermaid: string;
}

export interface PhaseInfo {
  phase_order: string[];
  gates: Record<string, unknown>;
}

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, init);
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

const jsonPost = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const api = {
  getProjects: () => fetchJSON<Project[]>('/projects'),
  createProject: (data: { name: string; description: string }) =>
    fetchJSON<Project>('/projects', jsonPost(data)),
  deleteProject: (id: string) =>
    fetchJSON<unknown>(`/projects/${id}`, { method: 'DELETE' }),

  getTasks: (projectId?: string) =>
    fetchJSON<Task[]>(projectId ? `/tasks?project_id=${projectId}` : '/tasks'),
  getTask: (id: string) => fetchJSON<Task>(`/tasks/${id}`),
  createRequirement: (data: {
    project_id: string;
    title: string;
    description: string;
    priority: string;
  }) =>
    fetchJSON<{ task_id: string; state: string; message: string }>(
      '/requirements',
      jsonPost(data),
    ),
  approveTask: (
    id: string,
    data: { approver: string; decision: 'approve' | 'reject'; comment: string },
  ) =>
    fetchJSON<{ task_id: string; state: string; message: string }>(
      `/tasks/${id}/approve`,
      jsonPost(data),
    ),
  retryTask: (id: string) =>
    fetchJSON<{ task_id: string; state: string; message: string }>(
      `/tasks/${id}/retry`,
      { method: 'POST' },
    ),

  getSpec: (id: string) =>
    fetchJSON<Record<string, unknown>>(`/tasks/${id}/spec`),
  getArchitecture: (id: string) =>
    fetchJSON<Record<string, unknown>>(`/tasks/${id}/architecture`),
  getImplementation: (id: string) =>
    fetchJSON<Record<string, unknown>>(`/tasks/${id}/implementation`),
  getReview: (id: string) =>
    fetchJSON<Record<string, unknown>>(`/tasks/${id}/review`),
  getTestReport: (id: string) =>
    fetchJSON<Record<string, unknown>>(`/tasks/${id}/test-report`),
  getDeployment: (id: string) =>
    fetchJSON<Record<string, unknown>>(`/tasks/${id}/deployment`),

  getHealth: () => fetchJSON<HealthStatus>('/health'),
  getPhases: () => fetchJSON<PhaseInfo>('/phases'),
  getWorkflowGraph: () => fetchJSON<WorkflowGraph>('/workflow/graph'),
  getEvaluation: () => fetchJSON<EvaluationSummary>('/evaluation'),
  getTaskEvaluation: (id: string) =>
    fetchJSON<TaskEvaluation>(`/evaluation/${id}`),
  getMetrics: () => fetchJSON<Record<string, unknown>>('/observability/metrics'),
};
