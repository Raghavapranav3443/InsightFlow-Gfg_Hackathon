import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSchema, getOverview } from '../utils/api'
import { getSessionId } from '../utils/session'
import DynamicChart from '../components/DynamicChart'
import { InsightCard } from '../components/SharedComponents'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import styles from './AutoDashboard.module.css'

// ── Role colour map ────────────────────────────────────────────────────────────
const ROLE_COLORS = {
  continuous: '#3b82f6', score: '#8b5cf6', measure: '#f59e0b',
  dimension: '#10b981', id: '#6b7280', datetime: '#ef4444', text: '#94a3b8',
}

// ── Skeleton shimmer card ──────────────────────────────────────────────────────
function SkeletonCard({ label }) {
  return (
    <div className={styles.skeletonCard}>
      <div className={styles.skeletonTitle} />
      <div className={styles.skeletonChart} />
      {label && <div className={styles.skeletonLabel}>{label}</div>}
    </div>
  )
}

// ── Dataset meta strip ─────────────────────────────────────────────────────────
function DatasetMeta({ schema }) {
  if (!schema) return null
  const roleCount = schema.columns.reduce((acc, c) => {
    acc[c.role] = (acc[c.role] || 0) + 1; return acc
  }, {})
  return (
    <div className={styles.datasetMeta}>
      <div className={styles.metaItem}>
        <span className={styles.metaVal}>{schema.row_count?.toLocaleString() ?? '—'}</span>
        <span className={styles.metaLabel}>rows</span>
      </div>
      <div className={styles.metaDivider} />
      <div className={styles.metaItem}>
        <span className={styles.metaVal}>{schema.columns?.length ?? '—'}</span>
        <span className={styles.metaLabel}>columns</span>
      </div>
      <div className={styles.metaDivider} />
      {Object.entries(roleCount).map(([role, count]) => (
        <div key={role} className={styles.metaPill} style={{ '--rc': ROLE_COLORS[role] || '#94a3b8' }}>
          <span className={styles.metaPillDot} />
          <span>{count} {role}</span>
        </div>
      ))}
    </div>
  )
}

// ── Overview section ───────────────────────────────────────────────────────────
function OverviewSection({ overview, loading }) {
  if (loading) {
    return (
      <div className={styles.overviewSection}>
        <div className={styles.overviewLoading}>
          <span className={styles.spinner} /> Generating AI overview of your dataset…
        </div>
      </div>
    )
  }
  if (!overview) return null
  return (
    <div className={styles.overviewSection}>
      <div className={styles.overviewIcon}>✦</div>
      <div className={styles.overviewContent}>
        <h2 className={styles.overviewTitle}>AI Dataset Overview</h2>
        <p className={styles.overviewSummary}>{overview.summary}</p>
        {overview.expert_note && (
          <div className={styles.expertNote}>
            <span className={styles.expertLabel}>Expert note</span>
            {overview.expert_note}
          </div>
        )}
        {overview.column_groups?.length > 0 && (
          <div className={styles.columnGroups}>
            {overview.column_groups.map((g, i) => (
              <div key={i} className={styles.groupCard}>
                <div className={styles.groupName}>{g.group}</div>
                <div className={styles.groupDesc}>{g.description}</div>
                <div className={styles.groupCols}>
                  {g.columns?.map(c => (
                    <span key={c} className={styles.colChip}>{c}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
        {overview.suggested_questions?.length > 0 && (
          <div className={styles.suggestedQuestions}>
            <div className={styles.suggestLabel}>Suggested questions from AI:</div>
            {overview.suggested_questions.map((q, i) => (
              <div key={i} className={styles.suggestQ}>→ {q}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Single chart card ──────────────────────────────────────────────────────────
function ChartCard({ chart, index }) {
  return (
    <div className={styles.chartCard}>
      <div className={styles.chartCardHeader}>
        <div className={styles.chartTitle}>{chart.title}</div>
        <div className={styles.chartMeta}>
          <Badge variant="gray">{chart.type}</Badge>
          {(chart.raw_row_count ?? chart.rows?.length ?? 0) > 0 && (
            <Badge variant="blue">{chart.raw_row_count ?? chart.rows?.length} rows</Badge>
          )}
        </div>
      </div>
      {chart.note && <div className={styles.chartNote}>⚠ {chart.note}</div>}
      {chart._type_corrected && (
        <div className={styles.correctionBadge}>✓ Auto-corrected chart type</div>
      )}
      <div id={`auto-chart-${index}`}>
        {chart.warning ? (
          <div className={styles.chartWarning}>⚠ {chart.warning}</div>
        ) : (
          <DynamicChart
            type={chart.type}
            rows={chart.rows}
            xCol={chart.x_col}
            yCols={chart.y_cols}
            colorCol={chart.color_col}
          />
        )}
      </div>
      {chart.insight && (
        <div className={styles.chartInsight}>
          <InsightCard text={chart.insight} compact />
        </div>
      )}
    </div>
  )
}

// ── Batch status header ────────────────────────────────────────────────────────
function ProgressHeader({ total, done, error }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  return (
    <div className={styles.progressHeader}>
      <div className={styles.progressInfo}>
        <span className={styles.progressLabel}>
          {done < total
            ? `Generating insights… ${done} / ${total} complete`
            : error
              ? `${done} of ${total} generated (${error} failed)`
              : `All ${total} insights generated`}
        </span>
        <span className={styles.progressPct}>{pct}%</span>
      </div>
      <div className={styles.progressBar}>
        <div className={styles.progressFill} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────
const BATCH_SIZE   = 3    // charts per batch
const BATCH_DELAY  = 2000 // ms between batches

export default function AutoDashboard() {
  const navigate = useNavigate()

  const [schema,  setSchema]  = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const [overview,        setOverview]        = useState(null)
  const [overviewLoading, setOverviewLoading] = useState(false)

  // Charts accumulate progressively
  const [charts,      setCharts]      = useState([])
  const [totalCharts, setTotalCharts] = useState(0)
  const [failedCount, setFailedCount] = useState(0)
  const [generating,  setGenerating]  = useState(false)
  const [genDone,     setGenDone]     = useState(false)

  // ── Step 1: Load schema ──────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false
    async function init() {
      try {
        const s = await getSchema()
        if (cancelled) return
        setSchema(s)
        setLoading(false)
      } catch (err) {
        if (cancelled) return
        if (err.message?.includes('404') || err.message?.includes('Session not found')) {
          setError('no_dataset')
        } else {
          setError(err.message)
        }
        setLoading(false)
      }
    }
    init()
    return () => { cancelled = true }
  }, [])

  // ── Step 2: Once schema loaded, fetch overview + trigger auto-report ──────────
  useEffect(() => {
    if (!schema) return
    let cancelled = false
    async function fetchOverview() {
      setOverviewLoading(true)
      try {
        const ov = await getOverview()
        if (!cancelled) setOverview(ov)
      } catch { /* overview is optional */ }
      finally { if (!cancelled) setOverviewLoading(false) }
    }
    fetchOverview()
    return () => { cancelled = true }
  }, [schema])

  // ── Step 3: Trigger the auto-report in batches ───────────────────────────────
  const runAutoReport = useCallback(async () => {
    if (generating || genDone) return
    setGenerating(true)
    setCharts([])
    setFailedCount(0)

    const sid = getSessionId()

    // First call: /api/auto-report — returns multiple charts from the backend
    let autoCharts = []
    try {
      const res = await fetch('/api/auto-report', {
        method: 'POST',
        headers: { 'X-Session-ID': sid },
      })
      if (res.ok) {
        const data = await res.json()
        // auto-report returns { charts: [...] } or an array
        autoCharts = Array.isArray(data) ? data : (data.charts || [])
      }
    } catch (err) {
      console.warn('[AutoDashboard] auto-report failed:', err.message)
    }

    // Supplement with targeted queries if needed to hit ~10 charts
    const SUPPLEMENTAL_QUERIES = [
      'Show the distribution of the most important dimension column',
      'Compare average values of the top numeric metrics across main categories',
      'Show correlation between the two most important numeric columns',
      'What is the top 10 breakdown by the primary categorical column?',
      'Show overall summary statistics for the key measures',
      'What are the top performing segments in the dataset?',
    ]

    const needed = Math.max(0, 10 - autoCharts.length)
    const supplementQueries = SUPPLEMENTAL_QUERIES.slice(0, needed)

    // Split supplemental into batches
    const batches = []
    for (let i = 0; i < supplementQueries.length; i += BATCH_SIZE) {
      batches.push(supplementQueries.slice(i, i + BATCH_SIZE))
    }

    // Show auto-report charts immediately
    setTotalCharts(autoCharts.length + supplementQueries.length)
    if (autoCharts.length > 0) {
      setCharts(autoCharts)
    }

    // Run supplemental batches
    let accumulated = autoCharts.length
    let failed = 0
    for (let batchIdx = 0; batchIdx < batches.length; batchIdx++) {
      if (batchIdx > 0) {
        // Delay between batches to respect rate limits
        await new Promise(r => setTimeout(r, BATCH_DELAY))
      }
      const batch = batches[batchIdx]
      const results = await Promise.allSettled(
        batch.map(async (prompt) => {
          // Retry once on 429
          for (let attempt = 0; attempt < 2; attempt++) {
            try {
              const r = await fetch('/api/query', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-Session-ID': sid,
                },
                body: JSON.stringify({ prompt }),
              })
              if (r.status === 429 && attempt === 0) {
                await new Promise(r2 => setTimeout(r2, 5000))
                continue
              }
              if (!r.ok) throw new Error(`HTTP ${r.status}`)
              const data = await r.json()
              // Extract charts from query result
              return (data.charts || []).map(c => ({
                ...c,
                insight: data.insight || null,
                _prompt: prompt,
              }))
            } catch (err) {
              if (attempt === 1) throw err
            }
          }
        })
      )

      const newCharts = []
      for (const r of results) {
        if (r.status === 'fulfilled' && r.value?.length > 0) {
          newCharts.push(...r.value)
          accumulated += r.value.length
        } else {
          failed++
        }
      }
      if (newCharts.length > 0) {
        setCharts(prev => [...prev, ...newCharts])
      }
      setFailedCount(failed)
    }

    setTotalCharts(accumulated)
    setGenerating(false)
    setGenDone(true)
  }, [generating, genDone])

  useEffect(() => {
    if (schema && !generating && !genDone) {
      runAutoReport()
    }
  }, [schema]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Render: no dataset ───────────────────────────────────────────────────────
  if (!loading && error === 'no_dataset') {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>📊</div>
        <h2>No dataset loaded</h2>
        <p>Load a dataset to generate your AI-powered dashboard.</p>
        <div className={styles.emptyActions}>
          <Button variant="primary" size="lg" onClick={() => navigate('/upload')}>
            Upload a CSV →
          </Button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className={styles.pageLoading}>
        <span className={styles.spinner} />
        <span>Loading your dataset…</span>
      </div>
    )
  }

  if (error && error !== 'no_dataset') {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>⚠</div>
        <h2>Something went wrong</h2>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>{error}</p>
        <Button variant="ghost" onClick={() => window.location.reload()}>Retry</Button>
      </div>
    )
  }

  return (
    <div className={styles.page}>

      {/* ── Page header ──────────────────────────────────────────────────────── */}
      <div className={styles.pageHeader}>
        <div className={styles.headerLeft}>
          <div className={styles.pageTitle}>
            <span className={styles.pageTitleIcon}>✦</span>
            AI Dashboard
          </div>
          <div className={styles.pageSubtitle}>
            {schema?.dataset_name && (
              <span className={styles.datasetName}>{schema.dataset_name}</span>
            )}
            {schema && <DatasetMeta schema={schema} />}
          </div>
        </div>
        <div className={styles.headerRight}>
          <Button
            variant="primary"
            onClick={() => navigate('/explore')}
            title="Ask your own natural-language questions"
          >
            Ask your own question →
          </Button>
          <Button
            variant="ghost"
            onClick={() => { setGenDone(false); setCharts([]); runAutoReport() }}
            disabled={generating}
            title="Regenerate all charts"
          >
            ↺ Regenerate
          </Button>
        </div>
      </div>

      {/* ── AI Overview ───────────────────────────────────────────────────────── */}
      <div className={styles.section}>
        <OverviewSection overview={overview} loading={overviewLoading} />
      </div>

      {/* ── Charts section ────────────────────────────────────────────────────── */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Auto-Generated Insights</h2>
          <p className={styles.sectionSub}>
            AI-selected analytics based on your dataset's structure and column relationships.
          </p>
        </div>

        {/* Progress bar while generating */}
        {(generating || (genDone && charts.length > 0)) && (
          <ProgressHeader
            total={totalCharts}
            done={charts.length}
            error={failedCount}
          />
        )}

        {/* Chart grid */}
        <div className={styles.chartGrid}>
          {charts.map((chart, i) => (
            <ChartCard key={i} chart={chart} index={i} />
          ))}

          {/* Skeleton placeholders for pending charts */}
          {generating && Array.from({
            length: Math.max(0, Math.min(BATCH_SIZE, totalCharts - charts.length))
          }).map((_, i) => (
            <SkeletonCard key={`sk-${i}`} label="Generating…" />
          ))}
        </div>

        {/* Empty state if nothing generated */}
        {genDone && charts.length === 0 && (
          <div className={styles.noCharts}>
            <p>Could not generate charts automatically. Your dataset may need more structured data.</p>
            <Button variant="primary" onClick={() => navigate('/explore')}>
              Try asking manually →
            </Button>
          </div>
        )}
      </div>

      {/* ── CTA strip ─────────────────────────────────────────────────────────── */}
      {genDone && charts.length > 0 && (
        <div className={styles.ctaStrip}>
          <div className={styles.ctaText}>
            <div className={styles.ctaTitle}>Want deeper insights?</div>
            <div className={styles.ctaSub}>Ask your own questions in the Query Explorer — natural language, no SQL needed.</div>
          </div>
          <Button variant="primary" size="lg" onClick={() => navigate('/explore')}>
            Open Query Explorer →
          </Button>
        </div>
      )}
    </div>
  )
}
