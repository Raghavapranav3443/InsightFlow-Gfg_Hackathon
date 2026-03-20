import { useState, useEffect, useRef, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { getSchema, runRefine, getOverview } from '../utils/api'
import { makeClient } from '../lib/api/client'
import { useAuth } from '../contexts/AuthContext'
import { useQueryStream } from '../hooks/useQueryStream'
import { useDashboardStore } from '../zustand/useDashboardStore'
import { useUIStore } from '../zustand/useUIStore'
import { useToast } from '../components/ui/useToast'
import { useDatasetStore } from '../zustand/useDatasetStore'
import Modal from '../components/ui/Modal'
import Input from '../components/ui/Input'
import DynamicChart from '../components/DynamicChart'
import ExportButton from '../components/ExportButton'
import DiagnosticModal from '../components/DiagnosticModal'
import DataTable from '../components/DataTable'
import {
  KpiCard, InsightCard, CannotAnswer, ClarificationCard, SqlToggle, ChartSkeleton,
} from '../components/SharedComponents'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import styles from './QueryExplorer.module.css'
import { getSessionId } from '../utils/session'
import ChatBot from '../components/ChatBot'
import FullReportWidget from '../components/FullReportWidget'

const DEMO_CHIPS = [
  'Show customer distribution by shopping preference and city tier',
  'Compare average online vs store spending by gender and city tier',
  'Show age distribution of customers by shopping preference',
]

// ── sessionStorage helpers ─────────────────────────────────────────────────────
// Persist the last result so navigating away and back doesn't wipe the dashboard.
const SS_KEY      = 'insightflow_last_result'
const SS_PROMPT   = 'insightflow_last_prompt'
const SS_QUERY    = 'insightflow_last_query'
const SS_OVERVIEW = 'insightflow_overview'

function ssGet(key) {
  try { const v = sessionStorage.getItem(key); return v ? JSON.parse(v) : null } catch { return null }
}
function ssSet(key, val) {
  try { sessionStorage.setItem(key, JSON.stringify(val)) } catch {}
}
function ssClear() {
  try {
    sessionStorage.removeItem(SS_KEY)
    sessionStorage.removeItem(SS_PROMPT)
    sessionStorage.removeItem(SS_QUERY)
  } catch {}
}

function ssClearAll() {
  try {
    sessionStorage.removeItem(SS_KEY)
    sessionStorage.removeItem(SS_PROMPT)
    sessionStorage.removeItem(SS_QUERY)
    sessionStorage.removeItem(SS_OVERVIEW)
  } catch {}
}

// ── Real SSE pipeline progress (replaces fake timer) ──────────────────────────
function SseProgress({ label, pct }) {
  return (
    <div className={styles.pipelineProgress}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <div className={styles.pipelineLabel}>{label || 'Processing…'}</div>
        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>{pct}%</div>
      </div>
      <div style={{ height: 5, background: 'var(--border)', borderRadius: 999, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`,
          background: 'linear-gradient(90deg, var(--primary), #00c8a0)',
          borderRadius: 999, transition: 'width 0.35s ease'
        }} />
      </div>
    </div>
  )
}

// ── Correction badge ───────────────────────────────────────────────────────────
function CorrectionBadge({ chart }) {
  if (!chart._type_corrected) return null
  return (
    <div className="correction-badge">
      ✓ Auto-corrected: pie → bar
      <span className="correction-reason">(one category &gt;60% of total — pie would mislead)</span>
    </div>
  )
}

// ── AI Overview card ───────────────────────────────────────────────────────────
function OverviewCard({ overview, loading }) {
  const [expanded, setExpanded] = useState(false)
  if (loading) return (
    <div className={styles.overviewCard}>
      <div className="overview-loading">
        <span className="overview-spinner" />
        Analysing dataset with AI…
      </div>
    </div>
  )
  if (!overview) return null
  return (
    <div className={styles.overviewCard}>
      <div className={styles.overviewHeader}>
        <div className="overview-icon">✦</div>
        <div>
          <div className={styles.overviewTitle}>AI Dataset Overview</div>
          <div className={styles.overviewSummary}>{overview.summary}</div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => setExpanded(e => !e)}
          style={{ marginLeft: 'auto', flexShrink: 0 }}>
          {expanded ? 'Less ▲' : 'More ▼'}
        </button>
      </div>

      {expanded && (
        <div className="overview-body">
          {overview.expert_note && (
            <div className="overview-expert">
              <span className="overview-expert-label">Expert note</span>
              {overview.expert_note}
            </div>
          )}

          {overview.column_groups?.length > 0 && (
            <div className="overview-groups">
              {overview.column_groups.map((g, i) => (
                <div key={i} className="overview-group">
                  <div className="overview-group-name">{g.group}</div>
                  <div className="overview-group-desc">{g.description}</div>
                  <div className="overview-group-cols">
                    {g.columns?.map(c => (
                      <span key={c} className="badge badge-gray" style={{ fontSize: '0.7rem' }}>{c}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {overview.suggested_questions?.length > 0 && (
            <div className="overview-suggestions">
              <div className="overview-suggestions-label">Try asking:</div>
              {overview.suggested_questions.map((q, i) => (
                <div key={i} className="overview-suggestion-q">→ {q}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function QueryExplorer({ health }) {
  const location = useLocation()
  const { token, apiFetch, isAuthenticated } = useAuth()
  const { toast } = useToast()

  // API Client — memoised so it's stable across renders
  const client = useMemo(() => makeClient(apiFetch), [apiFetch])

  // Zustand stores
  const dashStore = useDashboardStore()
  const uiStore   = useUIStore()
  const datasetStore = useDatasetStore()

  const [schema,      setSchema]      = useState(null)
  const [loadError,   setLoadError]   = useState(null)
  const [query,       setQuery]       = useState(ssGet(SS_QUERY) || '')
  const [refineInput, setRefineInput] = useState('')
  const [refining,    setRefining]    = useState(false)
  const [lastPrompt,  setLastPrompt]  = useState(ssGet(SS_PROMPT) || '')
  const [showDiag,    setShowDiag]    = useState(false)
  const [overview,    setOverview]    = useState(ssGet(SS_OVERVIEW))
  const [overviewLoading, setOverviewLoading] = useState(false)

  // Save dashboard modal
  const [saveModalOpen, setSaveModalOpen] = useState(false)
  const [saveName,      setSaveName]      = useState('')
  const [saving,        setSaving]        = useState(false)

  // SSE stream
  const stream = useQueryStream({ token, datasetId: schema?.dataset_id ?? null })

  const loading    = stream.isStreaming
  const result     = stream.result ?? ssGet(SS_KEY)
  const queryError = stream.error
  
  // Dashboard view toggle: 'analytics' | 'data'
  const viewMode = uiStore.viewMode
  const setViewMode = uiStore.setViewMode
  const [isSchemaOpen, setIsSchemaOpen] = useState(true)
  
  const [showFullReport, setShowFullReport] = useState(false)
  const [highlightedChartId, setHighlightedChartId] = useState(null)
  const [isInsightsOpen, setIsInsightsOpen] = useState(true)

  const initialQueryFired = useRef(false)



  // ── Load schema (passive — no auto-ingest) ───────────────────────────────────
  // We no longer auto-load the dataset on Dashboard mount. The user must
  // explicitly load a dataset via the Upload page first. This eliminates the
  // startup race condition where preload fails because the server just started.
  // If a session already has a dataset loaded (from Upload or a previous visit),
  // we just fetch the schema cheaply. If not, show the "no dataset" prompt.
  useEffect(() => {
    let cancelled = false
    async function init() {
      setLoadError(null)
      try {
        // 1. Fetch datasets list for the switcher (auth-only)
        if (isAuthenticated) {
          try {
            const list = await client.listDatasets()
            if (!cancelled) datasetStore.setDatasets(list)
          } catch { /* list is optional — ignore */ }
        }

        // 2. Load active schema for current session
        const s = await getSchema()
        if (cancelled) return
        setSchema(s)
        datasetStore.setSchema(s)

        // 3. Prefetch overview (silent — non-blocking)
        if (!ssGet(SS_OVERVIEW) && !cancelled) {
          try {
            const ov = await getOverview()
            if (!cancelled) {
              setOverview(ov)
              ssSet(SS_OVERVIEW, ov)
            }
          } catch { /* overview is optional */ }
        }
      } catch (err) {
        if (!cancelled) {
          const msg = err.message || ''
          if (msg.includes('404') || msg.includes('Session not found') || msg.includes('401')) {
            setSchema(null) // no dataset loaded yet — show the prompt
          } else {
            setLoadError(msg)
          }
        }
      }
    }
    init()
    return () => { cancelled = true }
  }, [isAuthenticated]) // eslint-disable-line react-hooks/exhaustive-deps

  // Handle dataset switch from dropdown
  async function handleDatasetSwitch(id) {
    if (!id || id === schema?.dataset_id) return
    uiStore.setGlobalLoading(true)
    try {
      // Normally we'd fetch schema by ID or activate it session-side.
      // Since backend requires setting the session, we'll optimistically update ID 
      // but warn it's partial if backend doesn't support changing session datset.
      // Wait, let's hit the GET /datasets/{id} endpoint via legacyFetch to see if it sets session... 
      // Our API plan says we just fetch it via `apiFetch('/api/datasets/'+id)`.
      const res = await apiFetch(`/api/datasets/${id}`)
      if (!res.ok) throw new Error('Failed to load dataset')
      const targetDataset = await res.json()
      
      const newSchema = { dataset_id: id, dataset_name: targetDataset.name, columns: [], row_count: 0 }
      setSchema(newSchema)
      datasetStore.setSchema(newSchema)
      flushDashboard()
      dashStore.setHistory([])
      toast.warning('Switched dataset (waiting for backend session sync)')
    } catch(e) {
      toast.error('Could not switch dataset.')
    } finally {
      uiStore.setGlobalLoading(false)
    }
  }

  // ── Fire initial query from Landing exactly once ──────────────────────────────
  useEffect(() => {
    if (!schema || initialQueryFired.current) return
    const iq = location.state?.initialQuery
    if (!iq) return
    initialQueryFired.current = true
    setQuery(iq)
    submitQuery(iq)
  }, [schema]) // eslint-disable-line react-hooks/exhaustive-deps

  // Update Zustand store when stream completes
  useEffect(() => {
    if (stream.result?.brief_insights?.length > 0) setIsInsightsOpen(true)
    if (stream.result) {
      ssSet(SS_KEY, stream.result)
      dashStore.setResult(stream.result, lastPrompt)
    }
  }, [stream.result]) // eslint-disable-line

  async function submitQuery(overridePrompt = null) {
    const text = (typeof overridePrompt === 'string' ? overridePrompt : query).trim()
    if (!text) return
    setLastPrompt(text)
    ssSet(SS_PROMPT, text)
    ssSet(SS_QUERY, text)
    await stream.run(text)
  }

  // ── Refine ────────────────────────────────────────────────────────────────────
  async function submitRefine() {
    const text = refineInput.trim()
    if (!text) return
    setRefining(true)
    setQueryError(null)
    try {
      const res = await runRefine(text, lastPrompt)
      setResult(res)
      const newPrompt = `${lastPrompt} → ${text}`
      setLastPrompt(newPrompt)
      ssSet(SS_KEY, res)
      ssSet(SS_PROMPT, newPrompt)
      setRefineInput('')
    } catch (err) {
      setQueryError(err.message)
    } finally {
      setRefining(false)
    }
  }

  // ── Save Dashboard ───────────────────────────────────────────────────────────
  async function handleSaveDashboard() {
    if (!saveName.trim() || !result) return
    setSaving(true)
    try {
      const sid = getSessionId()
      const res = await fetch('/api/save-dashboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-ID': sid },
        body: JSON.stringify({ name: saveName.trim(), data: result, prompt: lastPrompt }),
      })
      if (!res.ok) throw new Error('Save failed')
      const saved = await res.json()
      dashStore.addSaved(saved)
      setSaveModalOpen(false)
      setSaveName('')
      toast.success(`Dashboard "${saveName.trim()}" saved!`)
    } catch {
      toast.error('Could not save dashboard. Try again.')
    } finally {
      setSaving(false)
    }
  }

  // ── Flush dashboard ───────────────────────────────────────────────────────────
  function flushDashboard() {
    stream.reset()
    setQuery('')
    setLastPrompt('')
    setRefineInput('')
    ssClear()
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitQuery() }
  }

  const roleCount = schema
    ? schema.columns.reduce((acc, c) => { acc[c.role] = (acc[c.role] || 0) + 1; return acc }, {})
    : {}

  return (
    <div className={styles.layout}>

      {/* ══ SIDEBAR ══════════════════════════════════════════════════════════════ */}
      <aside className={`${styles.sidebar} ${!isSchemaOpen ? styles.sidebarCollapsed : ''}`}>

        {/* Panel tabs */}
        <div className={styles.sidebarTabs}>
          {['schema', 'history', 'saved'].map(panel => (
            <button
              key={panel}
              className={`${styles.sidebarTab} ${isSchemaOpen && uiStore.sidebarPanel === panel ? styles.sidebarTabActive : ''}`}
              onClick={() => { uiStore.setSidebarPanel(panel); if (!isSchemaOpen) setIsSchemaOpen(true) }}
            >
              {{ schema: '📋', history: '🕐', saved: '💾' }[panel]}
              {' '}{{ schema: 'Schema', history: 'History', saved: 'Saved' }[panel]}
            </button>
          ))}
        </div>

        <div className={styles.contentArea}>

          {/* ── SCHEMA PANEL ── */}
          {uiStore.sidebarPanel === 'schema' && (
            !schema ? (
              <div style={{ padding: 20 }}>
                {loadError ? (
                  <div style={{ fontSize: '0.8rem', color: 'var(--danger)', lineHeight: 1.65 }}>
                    <strong>Error:</strong><br />{loadError}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>No dataset loaded</div>
                    Go to{' '}
                    <a href="/upload" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 600 }}
                      onClick={e => { e.preventDefault(); window.location.href = '/upload' }}>Upload</a>
                    {' '}to load a dataset.
                  </div>
                )}
              </div>
            ) : isSchemaOpen ? (
              <>
                <div style={{ padding: '0 16px 16px' }}>
                  <div className={styles.datasetName} style={{ fontWeight: 600, marginBottom: 4 }}>{schema.dataset_name}</div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <span className="meta-pill">{schema.row_count.toLocaleString()} rows</span>
                    <span className="meta-pill">{schema.columns.length} cols</span>
                    {!schema.has_date_column && <span className="meta-pill warn">⚠ No date col</span>}
                  </div>
                </div>
                <div className={styles.sidebarSection}>
                  <div className={styles.sidebarSectionLabel}>Column Types</div>
                  <div className={styles.roleBreakdown}>
                    {Object.entries(roleCount).map(([role, count]) => (
                      <div className={styles.roleRow} key={role}>
                        <div className={styles.roleLabelWrap}>
                          <div className={`role-dot role-${role}`} />
                          <span style={{ fontSize: '0.79rem' }}>{role}</span>
                        </div>
                        <span className={styles.roleCount}>{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className={styles.sidebarSection} style={{ borderBottom: 'none' }}>
                  <div className={styles.sidebarSectionLabel}>All Columns</div>
                  <div className={styles.colList}>
                    {schema.columns.map(c => (
                      <div className={styles.colItem} key={c.safe_name}
                        title={`${c.original_name} · ${c.role} · ${c.nunique} unique values`}>
                        <div className={`role-dot role-${c.role}`} style={{ flexShrink: 0 }} />
                        <span className={styles.colItemName}>{c.safe_name}</span>
                        {c.is_ambiguous && <span title="Ambiguous" style={{ color: 'var(--warning)' }}>⚠</span>}
                        <span className={styles.colItemNunique}>{c.nunique}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : null
          )}

          {/* ── HISTORY PANEL ── */}
          {uiStore.sidebarPanel === 'history' && (
            <div style={{ padding: '8px 0' }}>
              {dashStore.history.length === 0 ? (
                <div style={{ padding: 20, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  No queries yet. Ask a question to build your history.
                </div>
              ) : dashStore.history.map(entry => (
                <button key={entry.id} onClick={() => {
                  dashStore.restoreFromHistory(entry)
                  setLastPrompt(entry.prompt)
                  setQuery(entry.prompt)
                  ssSet(SS_KEY, entry.result)
                  ssSet(SS_PROMPT, entry.prompt)
                }} className={styles.historyItem} title={entry.prompt}>
                  <div className={styles.historyPrompt}>{entry.prompt}</div>
                  <div className={styles.historyMeta}>{entry.result?.charts?.length ?? 0} charts</div>
                </button>
              ))}
            </div>
          )}

          {/* ── SAVED DASHBOARDS PANEL ── */}
          {uiStore.sidebarPanel === 'saved' && (
            <div style={{ padding: '8px 0' }}>
              {dashStore.saved.length === 0 ? (
                <div style={{ padding: 20, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  No saved dashboards yet. Run a query then click 💾 Save.
                </div>
              ) : dashStore.saved.map(d => (
                <button key={d.id} className={styles.historyItem}
                  onClick={() => {
                    dashStore.restoreFromHistory({ result: d.data, prompt: d.name })
                    setLastPrompt(d.name)
                    ssSet(SS_KEY, d.data)
                  }} title={d.name}>
                  <div className={styles.historyPrompt}>{d.name}</div>
                  <div className={styles.historyMeta}>{d.data?.charts?.length ?? 0} charts</div>
                </button>
              ))}
            </div>
          )}

        </div>
      </aside>


      {/* ══ MAIN ════════════════════════════════════════════════════════════════ */}
      <div className={styles.main}>

        {/* Status bar */}
        <div className={styles.statusBar}>
          <Button variant="ghost" size="sm" onClick={() => setIsSchemaOpen(!isSchemaOpen)} style={{ padding: '4px 8px', marginRight: 16, fontSize: '1.2rem', display: 'flex', alignItems: 'center' }} title="Toggle Data Dictionary">
            ☰
          </Button>
          <div className={styles.statusItem} onClick={() => setShowDiag(true)}
            title="Click to open diagnostics" style={{ cursor: 'pointer' }}>
            <span className={`status-dot ${health?.groq_key_looks_valid ? '' : 'error'}`} />
            <span>Groq {health?.groq_key_looks_valid ? 'ready' : 'key invalid'}</span>
          </div>
          <div className={styles.statusItem}>
            <span className={`status-dot ${schema ? '' : 'warn'}`} />
            <span>
              {schema ? (
                isAuthenticated && datasetStore.datasets.length > 0 ? (
                  <select 
                    value={schema.dataset_id || ''} 
                    onChange={e => handleDatasetSwitch(e.target.value)}
                    style={{ background: 'transparent', border: 'none', color: 'inherit', fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer', outline: 'none' }}
                  >
                    <option value={schema.dataset_id || ''}>{schema.dataset_name}</option>
                    {datasetStore.datasets
                      .filter(d => d.id !== schema.dataset_id)
                      .map(d => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                      ))}
                  </select>
                ) : (
                  `${schema.dataset_name} · ${schema.row_count?.toLocaleString()} rows · ${schema.columns?.length || 0} cols`
                )
              ) : 'No dataset — go to Upload'}
            </span>
          </div>
          
          {schema && (
            <div className={styles.viewToggle} style={{ marginLeft: 20, display: 'flex', gap: 4, background: 'var(--surface-2)', padding: 4, borderRadius: 'var(--radius)' }}>
              <Button 
                variant={viewMode === 'analytics' ? 'primary' : 'ghost'} size="sm"
                onClick={() => setViewMode('analytics')}
                style={{ margin: 0 }}>Analytics</Button>
              <Button 
                variant={viewMode === 'data' ? 'primary' : 'ghost'} size="sm"
                onClick={() => setViewMode('data')}
                style={{ margin: 0 }}>Raw Data</Button>
            </div>
          )}

          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            {schema && (
               <Button variant="primary" size="sm" onClick={() => setShowFullReport(true)}
                  title="Generate a comprehensive 4-chart business report autonomously">
                  ✦ Generate Full Report
               </Button>
            )}
            {result && viewMode === 'analytics' && (
              <>
                <ExportButton targetId="results-area" prompt={lastPrompt} result={result} />
                <Button variant="ghost" size="sm" onClick={flushDashboard}
                  title="Clear the current dashboard results">
                  ✕ Clear
                </Button>
              </>
            )}
            <Button variant="ghost" size="sm" onClick={() => setShowDiag(true)}>
              ⚙ Diagnostics
            </Button>
          </div>
        </div>

        {viewMode === 'data' ? (
          <div style={{ padding: '0 28px', marginTop: 24 }}>
            <div style={{ marginBottom: 16 }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Raw Dataset Preview</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>A rapid tabular view of your connected data.</p>
            </div>
            <DataTable />
          </div>
        ) : (
          <>
            <div className={styles.analyticsView}>
            {/* AI Overview */}
            <OverviewCard overview={overview} loading={overviewLoading} />

            {/* AI Insights & Answer (Merged) */}
            {(!result?.cannot_answer && (result?.insight || result?.brief_insights?.length > 0)) && (
              <div className="card" style={{ marginBottom: 24, background: 'var(--surface)', border: '1px solid var(--primary-muted)', borderRadius: 'var(--radius-lg)' }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', gap: 10, background: 'var(--surface-secondary)', borderTopLeftRadius: 'var(--radius-lg)', borderTopRightRadius: 'var(--radius-lg)' }}>
                  <span style={{ fontSize: '1.2rem', color: 'var(--primary)' }}>✦</span>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0, color: 'var(--primary)' }}>AI Question Overview</h3>
                </div>
                
                <div style={{ padding: '20px' }}>
                  {result.insight && (
                    <div style={{ marginBottom: result.brief_insights?.length ? 20 : 0 }}>
                      <InsightCard text={result.insight} />
                    </div>
                  )}
                  
                  {result.brief_insights?.length > 0 && (
                    <div style={{ background: 'var(--app-bg)', padding: 16, borderRadius: 'var(--radius)', border: '1px solid var(--border-light)' }}>
                      <h4 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', marginBottom: 12 }}>Key Takeaways</h4>
                      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {result.brief_insights.map((bi, i) => (
                          <li key={i} style={{ display: 'flex', gap: 10, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            <span style={{ color: 'var(--primary)', fontWeight: 'bold', marginTop: -2 }}>→</span>
                            <span style={{ lineHeight: 1.4 }}>{bi}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}

        {/* Query input */}


        {/* Results */}
        <div className={styles.resultsArea}>

          {queryError && (
            <div className={styles.cannotAnswer}>
              <div className={styles.cannotAnswerIcon} style={{ background: 'var(--danger)' }}>✕</div>
              <div>
                <h4>Request failed</h4>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', marginBottom: 6 }}>{queryError}</p>
                <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                  Check the terminal for{' '}
                  <code style={{ fontFamily: 'var(--font-mono)' }}>[LLM]</code> log lines,
                  or click ⚙ Diagnostics above.
                </p>
              </div>
            </div>
          )}

          {loading && (
            <div className="fade-in">
              <SseProgress label={stream.stepLabel} pct={stream.stepPct} />
              <ChartSkeleton count={2} />
            </div>
          )}

          {!loading && result && (
            <div id="results-area" className="fade-in">
              {result.cannot_answer && <CannotAnswer reason={result.reason} />}
              {result.clarification_needed && (
                <ClarificationCard 
                  prompt={result.clarification_prompt} 
                  onUse={(p) => { setQuery(p); submitQuery(p); }} 
                />
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
                  {result.charts.map((chart, i) => (
                <div className={`chart-card ${highlightedChartId === i ? 'highlighted' : ''}`} key={i} id={`chart-card-${i}`}>
                      <div className={styles.chartCardHeader}>
                        <div className={styles.chartTitle}>{chart.title}</div>
                        <div className={styles.chartMeta}>
                          <span className="badge badge-gray">{chart.type}</span>
                          {(chart.raw_row_count ?? chart.rows?.length ?? 0) > 0 && (
                            <span className="badge badge-blue">{chart.raw_row_count ?? chart.rows.length} rows</span>
                          )}
                          {(chart.raw_row_count ?? chart.rows?.length ?? 0) > 0 && (
                            <>
                              <button
                                className="btn btn-ghost btn-sm"
                                style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                                title="Download chart as PNG"
                                onClick={async () => {
                                  try {
                                    const el = document.getElementById(`chart-${i}`)
                                    if (!el) return
                                    const { toPng } = await import('html-to-image')
                                    const url = await toPng(el, { backgroundColor: '#ffffff' })
                                    const a = document.createElement('a')
                                    a.href = url
                                    a.download = `${chart.title.replace(/\s+/g, '_')}.png`
                                    a.click()
                                  } catch {}
                                }}
                              >
                                ↓ PNG
                              </button>
                              <button
                                className="btn btn-ghost btn-sm"
                                style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                                title="Download underlying data as CSV"
                                onClick={() => {
                                  const data = chart.spec?.data?.values || chart.rows
                                  if (!data || !data.length) {
                                    alert('No raw data available for this chart.')
                                    return
                                  }
                                  const keys = Object.keys(data[0])
                                  const csv = [
                                    keys.join(','),
                                    ...data.map(row => keys.map(k => JSON.stringify(row[k] ?? '')).join(','))
                                  ].join('\n')
                                  const blob = new Blob([csv], { type: 'text/csv' })
                                  const url = URL.createObjectURL(blob)
                                  const a = document.createElement('a')
                                  a.href = url
                                  a.download = `${chart.title.replace(/\s+/g, '_')}.csv`
                                  a.click()
                                  URL.revokeObjectURL(url)
                                }}
                              >
                                ↓ CSV
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                      <CorrectionBadge chart={chart} />
                      {chart.note && <div className="chart-note">⚠ {chart.note}</div>}
                      {chart.correlation_note && (
                        <div className="correlation-note">
                          <strong>Correlation:</strong> {chart.correlation_note}
                        </div>
                      )}
                      <div id={`chart-${i}`}>
                        {chart.warning ? (
                          <div className="chart-warning">⚠ {chart.warning}</div>
                        ) : (
                          <DynamicChart
                            type={chart.type} rows={chart.rows}
                            xCol={chart.x_col} yCols={chart.y_cols}
                            colorCol={chart.color_col}
                          />
                        )}
                      </div>
                      <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--border-light)' }}>
                        <SqlToggle sql={chart.sql} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {!result.cannot_answer && result.charts?.length > 0 && (
                <div className={styles.actionBar}>
                  <span className="action-bar-label" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span>
                      Query:{' '}
                      <em style={{ color: 'var(--text-secondary)' }}>
                        "{lastPrompt.length > 80 ? lastPrompt.slice(0, 80) + '…' : lastPrompt}"
                      </em>
                    </span>
                    {result.provider && (
                      <span className={`badge ${result.provider === 'gemini' ? 'badge-purple' : 'badge-yellow'}`} title={`Powered by ${result.provider === 'gemini' ? 'Google Gemini' : 'Groq'}`}>
                        {result.provider === 'gemini' ? '🔷 Gemini' : '⚡ Groq'}
                      </span>
                    )}
                  </span>
                  <ExportButton targetId="results-area" prompt={lastPrompt} result={result} />
                </div>
              )}

            </div>
          )}



          {!loading && !result && !queryError && !schema && (
            <div className={styles.emptyState}>
              <div className={styles.emptyStateIcon}>📊</div>
              <h3>No dataset loaded</h3>
              <p>Load a dataset first to start asking questions.</p>
              <a href="/upload"
                onClick={e => { e.preventDefault(); window.location.href = '/upload' }}
                className="btn btn-primary"
                style={{ display: 'inline-block', marginTop: 12 }}>
                Go to Upload →
              </a>
            </div>
          )}
          </div>
          </div>

          {schema && (
            <div className={styles.queryAreaBottom} style={{ left: isSchemaOpen ? 260 : 0, transition: 'left 0.3s ease' }}>
              <div className={styles.queryInputRow}>
                <textarea
                  className={styles.queryInput}
                  placeholder="Ask a deeper analytical question or prompt the AI..."
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={loading}
                  rows={1}
                />
                <Button variant="primary"
                  onClick={() => submitQuery()}
                  disabled={loading || !query.trim()}>
                  {loading ? '⏳' : '→'} Analyse
                </Button>
              </div>

              <div className={styles.suggestionSection}>
                <div className={styles.chipRow}>
                  {(result?.suggestions || DEMO_CHIPS).map(chip => (
                    <button key={chip}
                      className={`chip ${loading ? 'chip-loading' : ''} ${result?.suggestions ? 'suggestion-chip-active' : ''}`}
                      onClick={() => { setQuery(chip); submitQuery(chip) }}
                      disabled={loading}
                      title={chip}>
                      {chip.length > 54 ? chip.slice(0, 54) + '…' : chip}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
          </>
        )}
        </div>

      {showDiag && <DiagnosticModal health={health} onClose={() => setShowDiag(false)} />}
      {schema && <ChatBot context={result} />}
      {showFullReport && <FullReportWidget overview={overview} onComplete={() => setShowFullReport(false)} />}

      {/* ── Save Dashboard Modal ──────────────────────────────────────────────── */}
      <Modal open={saveModalOpen} onClose={() => { setSaveModalOpen(false); setSaveName('') }} title="Save Dashboard">
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: 16, marginTop: 0 }}>
          Give this dashboard a name. You can restore it later from the Saved panel.
        </p>
        <Input
          label="Dashboard name"
          placeholder="e.g. Customer Spending Overview"
          value={saveName}
          onChange={e => setSaveName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSaveDashboard()}
          autoFocus
        />
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 20 }}>
          <Button variant="ghost" size="sm" onClick={() => { setSaveModalOpen(false); setSaveName('') }}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={handleSaveDashboard}
            disabled={!saveName.trim() || saving}>
            {saving ? 'Saving…' : '💾 Save'}
          </Button>
        </div>
      </Modal>

    </div>
  )
}