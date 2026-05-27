import { useState, useEffect, useCallback, type FormEvent } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api, type Project, type Task } from '../api'

export default function ProjectDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [showForm, setShowForm] = useState(false)
  const [reqTitle, setReqTitle] = useState('')
  const [reqDesc, setReqDesc] = useState('')
  const [reqPriority, setReqPriority] = useState('P2')
  const [submitting, setSubmitting] = useState(false)

  const loadData = useCallback(async () => {
    if (!id) return
    try {
      const [projects, t] = await Promise.all([
        api.getProjects(),
        api.getTasks(id),
      ])
      setProject(projects.find((p) => p.id === id) ?? null)
      setTasks(t)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setSubmitting(true)
    try {
      await api.createRequirement({
        project_id: id,
        title: reqTitle,
        description: reqDesc,
        priority: reqPriority,
      })
      setReqTitle('')
      setReqDesc('')
      setReqPriority('P2')
      setShowForm(false)
      loadData()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create')
    } finally {
      setSubmitting(false)
    }
  }

  if (!id) {
    return (
      <div className="error-state">
        <p>No project ID</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="page-loader">
        <div className="spinner" />
        <p>Loading project…</p>
      </div>
    )
  }

  if (error && !project) {
    return (
      <div className="error-state">
        <div className="error-icon">⚠</div>
        <p>{error}</p>
      </div>
    )
  }

  return (
    <div className="page">
      <nav className="breadcrumb">
        <Link to="/">Dashboard</Link>
        <span className="breadcrumb__sep">/</span>
        <span>{project?.name || 'Project'}</span>
      </nav>

      <header className="page-header">
        <h1>{project?.name || 'Project'}</h1>
        {project?.description && (
          <p className="page-subtitle">{project.description}</p>
        )}
      </header>

      <section className="section">
        <div className="section-header">
          <h2>Tasks</h2>
          <button
            className="btn btn-primary"
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : '+ New Requirement'}
          </button>
        </div>

        {showForm && (
          <form className="glass-card create-form" onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Title</label>
                <input
                  className="input"
                  value={reqTitle}
                  onChange={(e) => setReqTitle(e.target.value)}
                  placeholder="Requirement title"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Priority</label>
                <select
                  className="select"
                  value={reqPriority}
                  onChange={(e) => setReqPriority(e.target.value)}
                >
                  <option value="P0">P0 — Critical</option>
                  <option value="P1">P1 — High</option>
                  <option value="P2">P2 — Medium</option>
                  <option value="P3">P3 — Low</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                className="textarea"
                value={reqDesc}
                onChange={(e) => setReqDesc(e.target.value)}
                placeholder="Describe the requirement in detail…"
                rows={4}
                required
              />
            </div>
            <button
              className="btn btn-primary"
              type="submit"
              disabled={submitting}
            >
              {submitting ? 'Submitting…' : 'Submit Requirement'}
            </button>
          </form>
        )}

        {tasks.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__icon">📋</div>
            <p>No tasks yet. Submit a requirement to begin.</p>
          </div>
        ) : (
          <div className="glass-card">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>State</th>
                  <th>Assignee</th>
                  <th>Phase</th>
                  <th>Priority</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr
                    key={t.id}
                    className="data-table__row--clickable"
                    onClick={() => navigate(`/tasks/${t.id}`)}
                  >
                    <td className="text-primary">{t.title}</td>
                    <td>
                      <span
                        className={`badge badge-${t.state.toLowerCase()}`}
                      >
                        {t.state}
                      </span>
                    </td>
                    <td className="text-muted">{t.assignee || '—'}</td>
                    <td className="text-muted">{t.current_phase || '—'}</td>
                    <td>
                      {t.priority ? (
                        <span
                          className={`badge badge-priority-${t.priority.toLowerCase()}`}
                        >
                          {t.priority}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {error && <div className="toast toast--error">{error}</div>}
    </div>
  )
}
