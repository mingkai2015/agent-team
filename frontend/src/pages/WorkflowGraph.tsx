import { useState, useEffect, useRef } from 'react'
import mermaid from 'mermaid'
import { api } from '../api'

export default function WorkflowGraph() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      themeVariables: {
        primaryColor: '#7b2ff7',
        primaryTextColor: '#e4e4e7',
        primaryBorderColor: '#7b2ff7',
        lineColor: '#00d4ff',
        secondaryColor: '#16161e',
        tertiaryColor: '#1e1e28',
        fontSize: '14px',
      },
    })

    api
      .getWorkflowGraph()
      .then(async (data) => {
        const { svg } = await mermaid.render('workflow-diagram', data.mermaid)
        if (containerRef.current) {
          containerRef.current.innerHTML = svg
        }
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Failed to load workflow'),
      )
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="page-loader">
        <div className="spinner" />
        <p>Loading workflow…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-state">
        <div className="error-icon">⚠</div>
        <p>{error}</p>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Workflow Graph</h1>
        <p className="page-subtitle">
          Agent delivery pipeline visualization
        </p>
      </header>
      <div className="glass-card workflow-container">
        <div ref={containerRef} className="mermaid-container" />
      </div>
    </div>
  )
}
