import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getHistory, clearHistory } from '../utils/api'
<<<<<<< HEAD
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import styles from './History.module.css'
=======
>>>>>>> 133e016e0e0b1defff61fad3bd011d924aeb6602

const CHART_TYPE_ICONS = {
  bar: '▦', grouped_bar: '▦▦', line: '∿', area: '◿', pie: '◑', scatter: '⁘'
}

function timeAgo(ts) {
  const diff = (Date.now() / 1000) - ts
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return new Date(ts * 1000).toLocaleDateString()
}

export default function History() {
  const [data,     setData]     = useState(null)
  const [error,    setError]    = useState(null)
  const [clearing, setClearing] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    getHistory()
      .then(setData)
      .catch(err => setError(err.message))
  }, [])

  function reloadQuery(prompt) {
    navigate('/dashboard', { state: { initialQuery: prompt } })
  }

  async function handleClear() {
    setClearing(true)
    try {
      await clearHistory()
      setData({ expired: false, items: [] })
    } catch (err) {
      setError(err.message)
    } finally {
      setClearing(false)
    }
  }

  if (error) return (
<<<<<<< HEAD
    <div className={styles.page}>
      <h1 className={styles.title}>Query History</h1>
      <div style={{ padding: '16px', marginTop: 32, background: 'var(--danger-bg)', border: '1px solid var(--danger)', borderRadius: '8px', color: 'var(--text-primary)', fontSize: '0.9rem' }}>
        <strong style={{ color: 'var(--danger)' }}>Error:</strong> {error}
=======
    <div className="history-page">
      <h1>Query History</h1>
      <div style={{ padding: '16px', background: 'var(--danger-bg)', borderRadius: 'var(--radius)', color: 'var(--danger)', fontSize: '0.825rem' }}>
        <strong>Error:</strong> {error}
>>>>>>> 133e016e0e0b1defff61fad3bd011d924aeb6602
      </div>
    </div>
  )

  if (!data) return (
<<<<<<< HEAD
    <div className={styles.page}>
      <h1 className={styles.title}>Query History</h1>
      <p className={styles.subtitle}>Loading your past analyses...</p>
      {[1,2,3].map(i => (
        <div key={i} style={{ height: 80, borderRadius: 8, marginBottom: 16, background: 'var(--surface-2)', animation: 'pulse 1.5s infinite' }} />
=======
    <div className="history-page">
      <h1>Query History</h1>
      {[1,2,3].map(i => (
        <div key={i} className="skeleton" style={{ height: 80, borderRadius: 12, marginBottom: 12 }} />
>>>>>>> 133e016e0e0b1defff61fad3bd011d924aeb6602
      ))}
    </div>
  )

  if (data.expired) return (
<<<<<<< HEAD
    <div className={styles.page}>
      <h1 className={styles.title}>Query History</h1>
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>⏱</div>
        <div className={styles.emptyTitle}>Session expired</div>
        <div className={styles.emptyText}>Sessions last 30 minutes. Return to the dashboard to start a new one.</div>
        <Button variant="primary" onClick={() => navigate('/dashboard')}>Go to Dashboard</Button>
=======
    <div className="history-page">
      <h1>Query History</h1>
      <div className="history-empty">
        <div style={{ fontSize: '2rem', marginBottom: 12 }}>⏱</div>
        <div style={{ fontWeight: 600, marginBottom: 6 }}>Session expired</div>
        <div style={{ fontSize: '0.825rem', marginBottom: 16 }}>Sessions last 30 minutes. Return to the dashboard to start a new one.</div>
        <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>Go to Dashboard</button>
>>>>>>> 133e016e0e0b1defff61fad3bd011d924aeb6602
      </div>
    </div>
  )

  if (!data.items?.length) return (
<<<<<<< HEAD
    <div className={styles.page}>
      <h1 className={styles.title}>Query History</h1>
      <p className={styles.subtitle}>Your query history for this session.</p>
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>📭</div>
        <div className={styles.emptyTitle}>No queries yet</div>
        <div className={styles.emptyText}>Head to the dashboard and ask your first question.</div>
        <Button variant="primary" onClick={() => navigate('/dashboard')}>Open Dashboard</Button>
=======
    <div className="history-page">
      <h1>Query History</h1>
      <p className="page-sub">Your query history for this session.</p>
      <div className="history-empty">
        <div style={{ fontSize: '2rem', marginBottom: 12 }}>📭</div>
        <div style={{ fontWeight: 600, marginBottom: 6 }}>No queries yet</div>
        <div style={{ fontSize: '0.825rem', marginBottom: 16 }}>Head to the dashboard and ask your first question.</div>
        <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>Open Dashboard</button>
>>>>>>> 133e016e0e0b1defff61fad3bd011d924aeb6602
      </div>
    </div>
  )

  const reversed = [...data.items].reverse()
  return (
<<<<<<< HEAD
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Query History</h1>
        <Button variant="secondary" size="sm" onClick={handleClear} disabled={clearing}>
          {clearing ? '…' : '✕ Clear history'}
        </Button>
      </div>
      <p className={styles.subtitle}>{data.items.length} queries this session</p>

      {reversed.map((item, i) => (
        <div className={styles.item} key={`${item.timestamp}-${i}`}>
          <div className={styles.itemNum}>{data.items.length - i}</div>
          <div className={styles.itemBody}>
            <div className={styles.prompt}>{item.prompt}</div>
            <div className={styles.meta}>
              <span>{timeAgo(item.timestamp)}</span>
              {item.cannot_answer
                ? <Badge variant="yellow">Cannot answer</Badge>
                : <>
                    {item.chart_specs?.map((c, j) => (
                      <Badge key={j} variant="gray">
                        {CHART_TYPE_ICONS[c.type] || '▦'} {c.type}
                      </Badge>
                    ))}
                    <Badge variant="blue">{item.kpi_specs?.length || 0} KPIs</Badge>
=======
    <div className="history-page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <h1 style={{ margin: 0 }}>Query History</h1>
        <button className="btn btn-secondary btn-sm" onClick={handleClear} disabled={clearing}>
          {clearing ? '…' : '✕ Clear history'}
        </button>
      </div>
      <p className="page-sub">{data.items.length} queries this session</p>

      {reversed.map((item, i) => (
        <div className="history-item" key={`${item.timestamp}-${i}`}>
          <div className="history-item-num">{data.items.length - i}</div>
          <div className="history-item-body">
            <div className="history-prompt">{item.prompt}</div>
            <div className="history-meta">
              <span>{timeAgo(item.timestamp)}</span>
              {item.cannot_answer
                ? <span className="badge badge-yellow">Cannot answer</span>
                : <>
                    {item.chart_specs?.map((c, j) => (
                      <span key={j} className="badge badge-gray">
                        {CHART_TYPE_ICONS[c.type] || '▦'} {c.type}
                      </span>
                    ))}
                    <span className="badge badge-blue">{item.kpi_specs?.length || 0} KPIs</span>
>>>>>>> 133e016e0e0b1defff61fad3bd011d924aeb6602
                  </>
              }
            </div>
            {item.insight && !item.cannot_answer && (
<<<<<<< HEAD
              <div className={styles.insight}>{item.insight}</div>
            )}
            {item.cannot_answer && item.reason && (
              <div className={styles.insight} style={{ color: 'var(--warning)', borderColor: 'var(--warning-bg)' }}>⚠ {item.reason}</div>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={() => reloadQuery(item.prompt)} title="Re-run this query" style={{ flexShrink: 0 }}>
            ↩ Rerun
          </Button>
=======
              <div className="history-insight">{item.insight}</div>
            )}
            {item.cannot_answer && item.reason && (
              <div className="history-insight" style={{ color: 'var(--warning)' }}>⚠ {item.reason}</div>
            )}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => reloadQuery(item.prompt)} title="Re-run this query">
            ↩ Rerun
          </button>
>>>>>>> 133e016e0e0b1defff61fad3bd011d924aeb6602
        </div>
      ))}
    </div>
  )
}