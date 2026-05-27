import { useState, useEffect, useCallback, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  api,
  type Project,
  type HealthStatus,
  type EvaluationSummary,
} from '../api'

export default function Dashboard() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [evaluation, setEvaluation] = useState<EvaluationSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [showForm, setShowForm] = useState(false)
  const [formName, setFormName] = useState('')
  const [formDesc, setFormDesc] = useState('')
  const [creating, setCreating] = useState(false)

  const loadData = useCallback(async () => {
    try {
      const [p, h, e] = await Promise.all([
        api.getProjects().catch(() => [] as Project[]),
        api.getHealth().catch(() => null),
        api.getEvaluation().catch(() => null),
      ])
      setProjects(p)
      setHealth(h)
      setEvaluation(e)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    setCreating(true)
    try {
      await api.createProject({ name: formName, description: formDesc })
      setFormName('')
      setFormDesc('')
      setShowForm(false)
      loadData()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create')
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this project?')) return
    try {
      await api.deleteProject(id)
      loadData()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete')
    }
  }

  if (loading) {
    return (
      <div className="page-loader">
        <div className="spinner" />
        <p>Loading dashboard…</p>
      </div>
    )
  }

  if (error && projects.length === 0) {
    return (
      <div className="error-state">
        <div className="error-icon">⚠</div>
        <p>{error}</p>
        <button
          className="btn btn-ghost"
          onClick={() => {
            setError('')
            setLoading(true)
            loadData()
          }}
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Mission Control</h1>
        <p className="page-subtitle">Agent Team IT Delivery Dashboard</p>
      </header>

      {/* Stats Row */}
      <div className="stats-grid">
        <div className="glass-card stats-card">
          <div className="stats-card__label">System Status</div>
          <div
            className={`stats-card__value ${health?.status === 'healthy' ? 'text-green' : 'text-orange'}`}
          >
            <span
              className={`status-dot ${health?.status === 'healthy' ? 'status-dot--online' : 'status-dot--warning'}`}
            />
            {health?.status ?? 'Unknown'}
          </div>
        </div>

        <div className="glass-card stats-card">
          <div className="stats-card__label">Total Tasks</div>
          <div className="stats-card__value text-cyan">
            {evaluation?.total_tasks ?? 0}
          </div>
        </div>

        <div className="glass-card stats-card">
          <div className="stats-card__label">Average Score</div>
          <div className="stats-card__value text-purple">
            {evaluation?.average_score?.toFixed(1) ?? '—'}
          </div>
        </div>

        <div className="glass-card stats-card">
          <div className="stats-card__label">Grade Distribution</div>
          <div className="grade-dist">
            {evaluation?.grade_distribution ? (
              Object.entries(evaluation.grade_distribution).map(
                ([grade, count]) => (
                  <span
                    key={grade}
                    className={`grade-chip grade-chip--${grade.toLowerCase()}`}
                  >
                    {grade}: {count}
                  </span>
                ),
              )
            ) : (
              <span className="text-muted">No data</span>
            )}
          </div>
        </div>
      </div>

      {/* Projects */}
      <section className="section">
        <div className="section-header">
          <h2>Projects</h2>
          <button
            className="btn btn-primary"
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : '+ New Project'}
          </button>
        </div>

        {showForm && (
          <form className="glass-card create-form" onSubmit={handleCreate}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Project Name</label>
                <input
                  className="input"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="My Project"
                  required
                />
              </div>
              <div className="form-group" style={{ flex: 2 }}>
                <label className="form-label">Description</label>
                <input
                  className="input"
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="Brief description…"
                  required
                />
              </div>
            </div>
            <button
              className="btn btn-primary"
              type="submit"
              disabled={creating}
            >
              {creating ? 'Creating…' : 'Create Project'}
            </button>
          </form>
        )}

        {projects.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__icon">📂</div>
            <p>No projects yet. Create one to get started.</p>
          </div>
        ) : (
          <div className="project-grid">
            {projects.map((p) => (
              <div
                key={p.id}
                className="glass-card project-card"
                onClick={() => navigate(`/projects/${p.id}`)}
              >
                <div className="project-card__header">
                  <h3 className="project-card__name">{p.name}</h3>
                  <button
                    className="btn-icon btn-icon--danger"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDelete(p.id)
                    }}
                    title="Delete project"
                  >
                    ✕
                  </button>
                </div>
                <p className="project-card__desc">{p.description}</p>
                {p.gitlab_mode && (
                  <span className="badge badge-default">{p.gitlab_mode}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {error && <div className="toast toast--error">{error}</div>}
    </div>
  )
}
