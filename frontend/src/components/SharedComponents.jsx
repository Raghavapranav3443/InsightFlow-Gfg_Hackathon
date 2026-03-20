import { useState } from 'react'
import { formatKpiValue } from '../utils/formatters'
import Button from './ui/Button'
import Badge from './ui/Badge'
import styles from './SharedComponents.module.css'

// ── KPI Card ───────────────────────────────────────────────────────────────────
export function KpiCard({ label, value, format }) {
  const isNull = value === null || value === undefined
  return (
    <div className={styles.kpiCard}>
      <div className={styles.kpiLabel}>{label}</div>
      <div className={`${styles.kpiValue} ${isNull ? styles.nullVal : ''}`}>
        {isNull ? '—' : formatKpiValue(value, format)}
      </div>
    </div>
  )
}

// ── AI Insight Card ────────────────────────────────────────────────────────────
export function InsightCard({ text }) {
  if (!text) return null

  // Backwards compatibility with plain text
  if (typeof text === 'string') {
    // If it's a markdown-style list (starts with *), parse it
    if (text.trim().startsWith('*')) {
      const bullets = text.split('\n').map(l => l.trim()).filter(l => l.startsWith('*')).map(l => l.replace(/^\*\s*/, ''))
      return (
        <div className={`${styles.insightCard} ${styles.structured}`}>
          <div className={styles.insightIcon}>✦</div>
          <div className={styles.insightContent}>
            <div className={styles.insightLabel}>AI Executive Summary</div>
            <ul className={styles.insightBullets}>
              {bullets.map((b, i) => {
                const isPositive = /\b(increase|growth|up|higher|improvement|top|performers)\b/i.test(b)
                const isNegative = /\b(decrease|drop|down|lower|loss|decline|anomaly|outlier|spike)\b/i.test(b)
                const icon = isPositive ? '📈' : isNegative ? '📉' : '●'
                return (
                  <li key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }}>
                    <span style={{ fontSize: '0.8rem' }}>{icon}</span>
                    <span>{b}</span>
                  </li>
                )
              })}
            </ul>
          </div>
        </div>
      )
    }
    return (
      <div className={styles.insightCard}>
        <div className={styles.insightIcon}>✦</div>
        <div className={styles.insightContent}>
          <div className={styles.insightLabel}>AI Insight</div>
          <div className={styles.insightText}>{text}</div>
        </div>
      </div>
    )
  }

  // Structured insight rendering (Task 9)
  const { headline, bullets = [], recommendation } = text
  
  if (!headline && bullets.length === 0 && !recommendation) return null
  
  return (
    <div className={`${styles.insightCard} ${styles.structured}`}>
      <div className={styles.insightIcon}>✦</div>
      <div className={styles.insightContent}>
        <div className={styles.insightLabel}>AI Insight</div>
        {headline && <div className={styles.insightHeadline}>{headline}</div>}
        {bullets.length > 0 && (
          <ul className={styles.insightBullets}>
            {bullets.map((b, i) => {
               const isPositive = /\b(increase|growth|up|higher|improvement|top|performers)\b/i.test(b)
               const isNegative = /\b(decrease|drop|down|lower|loss|decline|anomaly|outlier|spike)\b/i.test(b)
               const icon = isPositive ? '📈' : isNegative ? '📉' : '●'
               return (
                 <li key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }}>
                   <span style={{ fontSize: '0.8rem' }}>{icon}</span>
                   <span>{b}</span>
                 </li>
               )
            })}
          </ul>
        )}
        {recommendation && (
          <div className={styles.insightRecommendation}>
            <span style={{ fontWeight: 600, color: 'var(--primary)', marginRight: 6 }}>Action:</span>
            {recommendation}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Clarification Card (Task 11) ───────────────────────────────────────────────
export function ClarificationCard({ prompt, onUse }) {
  if (!prompt) return null
  return (
    <div className={styles.cannotAnswer} style={{ background: 'var(--info-bg)', borderColor: '#93c5fd' }}>
      <div className={styles.cannotAnswerIcon} style={{ background: 'var(--info)' }}>?</div>
      <div style={{ flex: 1 }}>
        <h4 style={{ color: 'var(--info)', marginBottom: 8 }}>Clarification Needed</h4>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: 16 }}>{prompt}</p>
        <Button variant="primary" size="sm" onClick={() => onUse(prompt)}>
          Use this phrasing
        </Button>
      </div>
    </div>
  )
}

// ── Cannot Answer Card ─────────────────────────────────────────────────────────
export function CannotAnswer({ reason }) {
  const technicalFailure = !reason || [
    'rate limit', 'timed out', 'unavailable', 'unexpected', 'groq',
    'api error', 'http', 'connection', 'parse', 'format', 'retry',
  ].some(kw => reason.toLowerCase().includes(kw))

  return (
    <div className={styles.cannotAnswer}>
      <div className={styles.cannotAnswerIcon}>!</div>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <h4 style={{ margin: 0 }}>
            {technicalFailure ? 'Could not answer this query' : 'Cannot answer this query'}
          </h4>
          {!technicalFailure && (
            <Badge variant="yellow" style={{ fontSize: '0.68rem' }}>
              Honesty by design
            </Badge>
          )}
        </div>
        <p style={{ fontSize: '0.845rem', lineHeight: 1.6, color: 'var(--text-secondary)', marginBottom: technicalFailure ? 0 : 8 }}>
          {reason || 'This question cannot be answered with the available data.'}
        </p>
        {!technicalFailure && (
          <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: 0 }}>
            InsightFlow refuses to fabricate data or generate charts with no factual basis.
            Other BI tools may produce confident-looking but incorrect results.
          </p>
        )}
      </div>
    </div>
  )
}

// ── SQL Toggle ─────────────────────────────────────────────────────────────────
export function SqlToggle({ sql }) {
  const [open, setOpen] = useState(false)
  if (!sql) return null
  return (
    <div>
      <button
        className={styles.sqlToggleBtn}
        onClick={() => setOpen(o => !o)}
        title="View the SQL generated for this chart"
      >
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.7rem', letterSpacing: '0.04em' }}>
          SQL
        </span>
        <span style={{ fontSize: '0.65rem', marginLeft: 2 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 4 }}>
            Generated SQL — executed read-only against SQLite
          </div>
          <pre className={styles.sqlBlock}>{sql}</pre>
        </div>
      )}
    </div>
  )
}

// ── Loading Skeleton ───────────────────────────────────────────────────────────
export function ChartSkeleton({ count = 2 }) {
  return (
    <div>
      <div className={styles.kpiGrid} style={{ marginBottom: 20 }}>
        {[1, 2, 3, 4].map(i => (
          <div key={i} className={`${styles.skeleton} ${styles.skeletonKpi}`} />
        ))}
      </div>
      <div className={styles.chartGrid}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={styles.card} style={{ padding: 20 }}>
            <div className={`${styles.skeleton} ${styles.skeletonText}`} style={{ width: '48%', marginBottom: 16 }} />
            <div className={`${styles.skeleton} ${styles.skeletonChart}`} />
          </div>
        ))}
      </div>
    </div>
  )
}