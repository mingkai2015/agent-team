import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, type Task, type TaskEvaluation } from '../api'

/* ─── Phase definitions ─── */

const PHASES = [
  { key: 'requirement', label: 'Requirement', agent: 'PM Agent' },
  { key: 'architecture', label: 'Architecture', agent: 'TL Agent' },
  { key: 'ux_design', label: 'UX Design', agent: 'UX Agent' },
  { key: 'implementation', label: 'Implementation', agent: 'Dev Agent' },
  { key: 'review', label: 'Code Review', agent: 'Reviewer' },
  { key: 'testing', label: 'Testing', agent: 'QA Agent' },
  { key: 'deployment', label: 'Deployment', agent: 'DevOps' },
]

const ARTIFACT_TABS = [
  { key: 'spec', label: 'Spec' },
  { key: 'architecture', label: 'Architecture' },
  { key: 'implementation', label: 'Implementation' },
  { key: 'review', label: 'Review' },
  { key: 'test-report', label: 'Test Report' },
  { key: 'deployment', label: 'Deployment' },
] as const

/* ─── Main Component ─── */

export default function TaskDetail() {
  const { id } = useParams()
  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<string>('spec')
  const [artifact, setArtifact] = useState<Record<string, unknown> | null>(
    null,
  )
  const [artifactLoading, setArtifactLoading] = useState(false)
  const [artifactError, setArtifactError] = useState('')
  const [evaluation, setEvaluation] = useState<TaskEvaluation | null>(null)
  const [logs, setLogs] = useState<
    Array<{ message: string; timestamp?: string }>
  >([])

  const [approver, setApprover] = useState('')
  const [comment, setComment] = useState('')
  const [approving, setApproving] = useState(false)

  const logsEndRef = useRef<HTMLDivElement>(null)

  /* ─ Fetch task ─ */
  const loadTask = useCallback(async () => {
    if (!id) return
    try {
      const t = await api.getTask(id)
      setTask(t)
      if (t.state === 'COMPLETED') {
        api.getTaskEvaluation(id).then(setEvaluation).catch(() => {})
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load task')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    loadTask()
  }, [loadTask])

  /* ─ SSE live progress ─ */
  useEffect(() => {
    if (!id) return
    const es = new EventSource(`/tasks/${id}/stream`)
    es.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data) as Record<string, unknown>
        setLogs((prev) => [
          ...prev,
          {
            message: String(data.message ?? evt.data),
            timestamp: data.timestamp ? String(data.timestamp) : undefined,
          },
        ])
        if (data.state || data.phase) loadTask()
      } catch {
        setLogs((prev) => [...prev, { message: evt.data }])
      }
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [id, loadTask])

  /* ─ Auto-scroll logs ─ */
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  /* ─ Fetch artifact per tab ─ */
  useEffect(() => {
    if (!id) return
    setArtifactLoading(true)
    setArtifactError('')
    setArtifact(null)

    const fetchers: Record<
      string,
      (taskId: string) => Promise<Record<string, unknown>>
    > = {
      spec: api.getSpec,
      architecture: api.getArchitecture,
      implementation: api.getImplementation,
      review: api.getReview,
      'test-report': api.getTestReport,
      deployment: api.getDeployment,
    }

    const fetcher = fetchers[activeTab]
    if (fetcher) {
      fetcher(id)
        .then(setArtifact)
        .catch((err: unknown) =>
          setArtifactError(
            err instanceof Error ? err.message : 'Not available yet',
          ),
        )
        .finally(() => setArtifactLoading(false))
    } else {
      setArtifactLoading(false)
    }
  }, [id, activeTab])

  /* ─ Approval ─ */
  async function handleApproval(decision: 'approve' | 'reject') {
    if (!id || !approver.trim()) return
    setApproving(true)
    try {
      await api.approveTask(id, { approver, decision, comment })
      setApprover('')
      setComment('')
      await loadTask()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Approval failed')
    } finally {
      setApproving(false)
    }
  }

  /* ─ Retry ─ */
  async function handleRetry() {
    if (!id) return
    try {
      await api.retryTask(id)
      await loadTask()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Retry failed')
    }
  }

  /* ─── Guards ─── */
  if (!id) {
    return (
      <div className="error-state">
        <p>No task ID</p>
      </div>
    )
  }
  if (loading) {
    return (
      <div className="page-loader">
        <div className="spinner" />
        <p>Loading task…</p>
      </div>
    )
  }
  if (error && !task) {
    return (
      <div className="error-state">
        <div className="error-icon">⚠</div>
        <p>{error}</p>
      </div>
    )
  }
  if (!task) {
    return (
      <div className="error-state">
        <p>Task not found</p>
      </div>
    )
  }

  const currentPhaseIndex = PHASES.findIndex(
    (p) => p.key === task.current_phase,
  )

  /* ─── Render ─── */
  return (
    <div className="page">
      {/* Breadcrumb */}
      <nav className="breadcrumb">
        <Link to="/">Dashboard</Link>
        {task.project_id && (
          <>
            <span className="breadcrumb__sep">/</span>
            <Link to={`/projects/${task.project_id}`}>Project</Link>
          </>
        )}
        <span className="breadcrumb__sep">/</span>
        <span>{task.title}</span>
      </nav>

      {/* Header */}
      <header className="task-header">
        <div className="task-header__info">
          <h1>{task.title}</h1>
          <div className="task-header__meta">
            <span className={`badge badge-${task.state.toLowerCase()}`}>
              {task.state}
            </span>
            {task.priority && (
              <span
                className={`badge badge-priority-${task.priority.toLowerCase()}`}
              >
                {task.priority}
              </span>
            )}
            {task.assignee && (
              <span className="task-header__assignee">
                🤖 {task.assignee}
              </span>
            )}
          </div>
        </div>
        <div className="task-header__actions">
          {task.state === 'REJECTED' && (
            <button className="btn btn-primary" onClick={handleRetry}>
              ↻ Retry
            </button>
          )}
        </div>
      </header>

      {task.description && (
        <p className="task-description">{task.description}</p>
      )}

      {/* ── Phase Timeline ── */}
      <div className="glass-card">
        <h3 className="card-title">Phase Progress</h3>
        <div className="phase-timeline">
          {PHASES.map((phase, idx) => {
            let status: 'completed' | 'active' | 'pending' = 'pending'
            if (task.state === 'COMPLETED') {
              status = 'completed'
            } else if (idx < currentPhaseIndex) {
              status = 'completed'
            } else if (idx === currentPhaseIndex) {
              status = 'active'
            }
            return (
              <div
                key={phase.key}
                className={`phase-step phase-step--${status}`}
              >
                <div className="phase-step__indicator">
                  {status === 'completed' ? '✓' : idx + 1}
                </div>
                {idx < PHASES.length - 1 && (
                  <div className="phase-step__connector" />
                )}
                <div className="phase-step__label">{phase.label}</div>
                <div className="phase-step__agent">{phase.agent}</div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Approval Panel ── */}
      {task.state === 'PENDING_APPROVAL' && (
        <div className="glass-card approval-panel">
          <h3 className="card-title">
            <span className="pulse-dot" />
            Approval Required — {task.current_gate || 'Gate'}
          </h3>
          <p className="approval-panel__info">
            Current assignee: <strong>{task.assignee}</strong>
          </p>
          <div className="form-group">
            <label className="form-label">Approver Name</label>
            <input
              className="input"
              value={approver}
              onChange={(e) => setApprover(e.target.value)}
              placeholder="Your name"
            />
          </div>
          <div className="form-group" style={{ marginTop: 12 }}>
            <label className="form-label">Comment</label>
            <textarea
              className="textarea"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Optional comment…"
              rows={3}
            />
          </div>
          <div className="approval-panel__actions">
            <button
              className="btn btn-approve"
              onClick={() => handleApproval('approve')}
              disabled={approving || !approver.trim()}
            >
              ✓ Approve
            </button>
            <button
              className="btn btn-reject"
              onClick={() => handleApproval('reject')}
              disabled={approving || !approver.trim()}
            >
              ✕ Reject
            </button>
          </div>
        </div>
      )}

      {/* ── SSE Progress Log ── */}
      {logs.length > 0 && (
        <div className="glass-card">
          <h3 className="card-title">Live Progress</h3>
          <div className="sse-log">
            {logs.map((log, i) => (
              <div key={i} className="sse-log__entry">
                {log.timestamp && (
                  <span className="sse-log__time">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                )}
                <span className="sse-log__msg">{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}

      {/* ── Artifact Tabs ── */}
      <div className="glass-card">
        <div className="tabs">
          {ARTIFACT_TABS.map((tab) => (
            <button
              key={tab.key}
              className={`tab ${activeTab === tab.key ? 'tab--active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="artifact-content">
          {artifactLoading ? (
            <div className="artifact-loader">
              <div className="spinner" />
            </div>
          ) : artifactError ? (
            <div className="artifact-empty">{artifactError}</div>
          ) : artifact ? (
            <ArtifactRenderer tabKey={activeTab} data={artifact} />
          ) : (
            <div className="artifact-empty">No data available</div>
          )}
        </div>
      </div>

      {/* ── Evaluation ── */}
      {evaluation && (
        <div className="glass-card">
          <h3 className="card-title">Evaluation</h3>
          <div className="eval-header">
            <div
              className={`grade-badge grade-badge--${evaluation.grade.toLowerCase()}`}
            >
              {evaluation.grade}
            </div>
            <div className="eval-total">
              <span className="eval-total__label">Total Score</span>
              <span className="eval-total__value">
                {evaluation.total_score.toFixed(1)}
              </span>
            </div>
          </div>
          <div className="eval-scores">
            {Object.entries(evaluation.scores).map(([key, val]) => (
              <div key={key} className="eval-score-card">
                <div className="eval-score-card__label">
                  {key.replace(/_/g, ' ')}
                </div>
                <div className="eval-score-card__value">{val.toFixed(1)}</div>
                <div className="eval-score-card__bar">
                  <div
                    className="eval-score-card__fill"
                    style={{ width: `${Math.min(val * 10, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Approval History ── */}
      {task.approvals && task.approvals.length > 0 && (
        <div className="glass-card">
          <h3 className="card-title">Approval History</h3>
          <div className="approval-history">
            {task.approvals.map((a, i) => (
              <div
                key={i}
                className={`approval-entry approval-entry--${a.decision}`}
              >
                <div className="approval-entry__dot" />
                <div className="approval-entry__content">
                  <div className="approval-entry__header">
                    <strong>{a.approver}</strong>
                    <span
                      className={`badge badge-${a.decision === 'approve' ? 'approved' : 'rejected'}`}
                    >
                      {a.decision}
                    </span>
                    {a.gate && (
                      <span className="approval-entry__gate">{a.gate}</span>
                    )}
                  </div>
                  {a.comment && (
                    <p className="approval-entry__comment">{a.comment}</p>
                  )}
                  <span className="approval-entry__time">
                    {new Date(a.timestamp).toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <div className="toast toast--error">{error}</div>}
    </div>
  )
}

/* ────────────────────────────────────────────────────
   Artifact sub-renderers
   ──────────────────────────────────────────────────── */

function ArtifactRenderer({
  tabKey,
  data,
}: {
  tabKey: string
  data: Record<string, unknown>
}) {
  switch (tabKey) {
    case 'spec':
      return <SpecView data={data} />
    case 'architecture':
      return <ArchitectureView data={data} />
    case 'implementation':
      return <ImplementationView data={data} />
    case 'review':
      return <ReviewView data={data} />
    case 'test-report':
      return <TestReportView data={data} />
    case 'deployment':
      return <DeploymentView data={data} />
    default:
      return <JsonFallback data={data} />
  }
}

/* ─ Spec ─ */
function SpecView({ data }: { data: Record<string, unknown> }) {
  const stories = Array.isArray(data.user_stories) ? data.user_stories : null
  const criteria = Array.isArray(data.acceptance_criteria)
    ? data.acceptance_criteria
    : null

  if (!stories && !criteria) return <JsonFallback data={data} />

  return (
    <div className="artifact-spec">
      {stories && (
        <div className="artifact-section">
          <h4>User Stories</h4>
          <div className="story-cards">
            {(stories as unknown[]).map((s, i) => (
              <div key={i} className="story-card">
                {typeof s === 'string' ? s : JSON.stringify(s, null, 2)}
              </div>
            ))}
          </div>
        </div>
      )}
      {criteria && (
        <div className="artifact-section">
          <h4>Acceptance Criteria</h4>
          <ul className="criteria-list">
            {(criteria as unknown[]).map((c, i) => (
              <li key={i}>
                {typeof c === 'string' ? c : JSON.stringify(c)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/* ─ Architecture ─ */
function ArchitectureView({ data }: { data: Record<string, unknown> }) {
  const techStack = Array.isArray(data.tech_stack) ? data.tech_stack : null
  const rawApis = data.api_list ?? data.apis
  const apis = Array.isArray(rawApis) ? (rawApis as unknown[]) : null

  return (
    <div className="artifact-arch">
      {techStack && (
        <div className="artifact-section">
          <h4>Tech Stack</h4>
          <div className="tech-badges">
            {(techStack as unknown[]).map((t, i) => (
              <span key={i} className="tech-badge">
                {String(t)}
              </span>
            ))}
          </div>
        </div>
      )}
      {apis && (
        <div className="artifact-section">
          <h4>API Endpoints</h4>
          <div className="api-list">
            {apis.map((a, i) => (
              <div key={i} className="api-item">
                {typeof a === 'string' ? a : JSON.stringify(a, null, 2)}
              </div>
            ))}
          </div>
        </div>
      )}
      {data.data_model != null && (
        <div className="artifact-section">
          <h4>Data Model</h4>
          <pre className="code-block">
            {typeof data.data_model === 'string'
              ? data.data_model
              : JSON.stringify(data.data_model, null, 2)}
          </pre>
        </div>
      )}
      {!techStack && !apis && !data.data_model && (
        <JsonFallback data={data} />
      )}
    </div>
  )
}

/* ─ Implementation ─ */
function ImplementationView({ data }: { data: Record<string, unknown> }) {
  const files = Array.isArray(data.files) ? data.files : null
  if (!files) return <JsonFallback data={data} />

  return (
    <div className="artifact-impl">
      {(files as unknown[]).map((f, i) => {
        const file = f as Record<string, unknown>
        return (
          <FileBlock
            key={i}
            path={String(file.path || file.name || `file_${i}`)}
            content={String(file.content || '')}
          />
        )
      })}
    </div>
  )
}

function FileBlock({ path, content }: { path: string; content: string }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="file-block">
      <div className="file-block__header" onClick={() => setExpanded(!expanded)}>
        <span className="file-block__icon">{expanded ? '▼' : '▶'}</span>
        <span className="file-block__path">{path}</span>
      </div>
      {expanded && <pre className="code-block">{content}</pre>}
    </div>
  )
}

/* ─ Review ─ */
function ReviewView({ data }: { data: Record<string, unknown> }) {
  const score = typeof data.score === 'number' ? data.score : null
  const issues = Array.isArray(data.issues) ? (data.issues as unknown[]) : null
  const suggestions = Array.isArray(data.suggestions)
    ? (data.suggestions as unknown[])
    : null

  return (
    <div className="artifact-review">
      {score !== null && (
        <div className="review-score">
          <span className="review-score__label">Review Score</span>
          <span
            className={`review-score__value ${score >= 8 ? 'text-green' : score >= 5 ? 'text-orange' : 'text-red'}`}
          >
            {score}/10
          </span>
        </div>
      )}
      {issues && (
        <div className="artifact-section">
          <h4>Issues</h4>
          {issues.map((issue, i) => {
            const iss = issue as Record<string, unknown>
            const severity = String(iss.severity || 'info').toLowerCase()
            return (
              <div key={i} className={`issue-card issue-card--${severity}`}>
                <span className="issue-card__severity">{severity}</span>
                <span>
                  {String(
                    iss.message || iss.description || JSON.stringify(issue),
                  )}
                </span>
              </div>
            )
          })}
        </div>
      )}
      {suggestions && (
        <div className="artifact-section">
          <h4>Suggestions</h4>
          <ul className="suggestions-list">
            {suggestions.map((s, i) => (
              <li key={i}>
                {typeof s === 'string' ? s : JSON.stringify(s)}
              </li>
            ))}
          </ul>
        </div>
      )}
      {score === null && !issues && !suggestions && (
        <JsonFallback data={data} />
      )}
    </div>
  )
}

/* ─ Test Report ─ */
function TestReportView({ data }: { data: Record<string, unknown> }) {
  const cases = Array.isArray(data.test_cases)
    ? (data.test_cases as unknown[])
    : null
  const results = Array.isArray(data.results)
    ? (data.results as unknown[])
    : null
  const items = cases || results

  if (!items) return <JsonFallback data={data} />

  return (
    <div className="artifact-test">
      <table className="data-table">
        <thead>
          <tr>
            <th>Test</th>
            <th>Status</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {items.map((t, i) => {
            const tc = t as Record<string, unknown>
            const status = String(
              tc.status || tc.result || 'unknown',
            ).toLowerCase()
            return (
              <tr key={i}>
                <td>{String(tc.name || tc.title || `Test ${i + 1}`)}</td>
                <td>
                  <span
                    className={`badge ${status === 'pass' || status === 'passed' ? 'badge-approved' : status === 'fail' || status === 'failed' ? 'badge-rejected' : 'badge-default'}`}
                  >
                    {status}
                  </span>
                </td>
                <td className="text-muted">
                  {String(tc.details || tc.message || '—')}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/* ─ Deployment ─ */
function DeploymentView({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="artifact-deploy">
      {Object.entries(data).map(([key, val]) => (
        <div key={key} className="deploy-field">
          <span className="deploy-field__key">{key}</span>
          <span className="deploy-field__value">
            {typeof val === 'string' ? (
              val
            ) : (
              <pre className="code-block code-block--inline">
                {JSON.stringify(val, null, 2)}
              </pre>
            )}
          </span>
        </div>
      ))}
    </div>
  )
}

/* ─ Fallback ─ */
function JsonFallback({ data }: { data: Record<string, unknown> }) {
  return <pre className="code-block">{JSON.stringify(data, null, 2)}</pre>
}
