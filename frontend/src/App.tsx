import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ProjectDetail from './pages/ProjectDetail'
import TaskDetail from './pages/TaskDetail'
import WorkflowGraph from './pages/WorkflowGraph'

export default function App() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar__logo">
          <span className="sidebar__logo-icon">◉</span>
          <div>
            <div className="sidebar__logo-title">Agent Team</div>
            <div className="sidebar__logo-subtitle">Mission Control</div>
          </div>
        </div>

        <nav className="sidebar__nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`
            }
          >
            <span className="sidebar__link-icon">⬡</span>
            Dashboard
          </NavLink>
          <NavLink
            to="/workflow"
            className={({ isActive }) =>
              `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`
            }
          >
            <span className="sidebar__link-icon">⬢</span>
            Workflow
          </NavLink>
        </nav>

        <div className="sidebar__footer">
          <div className="sidebar__version">v0.1.0</div>
        </div>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/tasks/:id" element={<TaskDetail />} />
          <Route path="/workflow" element={<WorkflowGraph />} />
        </Routes>
      </main>
    </div>
  )
}
