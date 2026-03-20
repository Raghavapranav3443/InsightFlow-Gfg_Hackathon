import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import DynamicChart from '../components/DynamicChart'
import { InsightCard, KpiCard } from '../components/SharedComponents'
import Spinner from '../components/ui/Spinner'
import Button from '../components/ui/Button'
import styles from './SharedDashboard.module.css'

export default function SharedDashboard() {
  const { token } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`/api/share/${token}`)
        if (!res.ok) throw new Error(
          res.status === 404 ? 'Dashboard not found or link expired.' : 'Failed to load shared dashboard.'
        )
        const dash = await res.json()
        setData(dash)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token])

  if (loading) return <div className={styles.center}><Spinner size={32} /></div>
  if (error) return (
    <div className={styles.center}>
      <div className={styles.errorBox}>
        <div style={{ fontSize: '2rem', marginBottom: 12 }}>🔗</div>
        <h2>Invalid Link</h2>
        <p>{error}</p>
        <Link to="/"><Button variant="primary" style={{ marginTop: 20 }}>Go to InsightFlow</Button></Link>
      </div>
    </div>
  )

  // Dashboard data comes as { name, data: { charts, kpis, insight, ... } }
  const result = data?.data ?? data
  if (!result) return (
    <div className={styles.center}><p>No dashboard data found.</p></div>
  )

  return (
    <div className={styles.layout}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>{data.name || 'Shared Dashboard'}</h1>
          <p className={styles.subtitle}>Shared via InsightFlow</p>
        </div>
        <Link to="/"><Button variant="primary" size="sm">Create your own</Button></Link>
      </div>

      <div className={styles.content}>
        {result.insight && (
          <div style={{ marginBottom: 24 }}>
            <InsightCard text={result.insight} />
          </div>
        )}

        {result.kpis?.length > 0 && (
          <div className={styles.kpiGrid}>
            {result.kpis.map((k, i) => (
              <KpiCard key={i} label={k.label} value={k.value} format={k.format} />
            ))}
          </div>
        )}

        {result.charts?.length > 0 && (
          <div className={styles.chartGrid}>
            {result.charts.map((c, i) => (
              <div key={i} className={styles.chartCard} id={`chart-card-${i}`}>
                <div className={styles.chartHeader}>
                  <h4 className={styles.chartTitle}>{c.title}</h4>
                </div>
                <div id={`chart-${i}`}>
                  <DynamicChart
                    type={c.type}
                    rows={c.rows}
                    columns={c.columns}
                    title={c.title}
                    error={null}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {(!result.charts?.length && !result.kpis?.length) && (
          <div className={styles.center} style={{ paddingTop: 60 }}>
            <p style={{ color: 'var(--text-muted)' }}>This dashboard has no charts or KPIs.</p>
          </div>
        )}
      </div>
    </div>
  )
}
