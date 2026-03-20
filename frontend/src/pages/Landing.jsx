import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { preloadDataset } from '../utils/api'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import styles from './Landing.module.css'

// ── Typewriter effect for the terminal ────────────────────────────────────────
function useTypewriter(text, speed = 28, startDelay = 0) {
  const [displayed, setDisplayed] = useState('')
  const [done, setDone]           = useState(false)
  useEffect(() => {
    setDisplayed('')
    setDone(false)
    let i = 0
    const timeout = setTimeout(() => {
      const interval = setInterval(() => {
        i++
        setDisplayed(text.slice(0, i))
        if (i >= text.length) { clearInterval(interval); setDone(true) }
      }, speed)
      return () => clearInterval(interval)
    }, startDelay)
    return () => clearTimeout(timeout)
  }, [text, speed, startDelay])
  return { displayed, done }
}

// ── Animated terminal / demo panel ────────────────────────────────────────────
const TERMINAL_STEPS = [
  { type: 'input',  text: 'Show customer distribution by shopping preference and city tier',  delay: 400  },
  { type: 'step',   text: '→ Building SQL query…',                                            delay: 1600 },
  { type: 'sql',    text: 'SELECT "shopping_preference", "city_tier", COUNT(*) as "count"\\nFROM customer_behaviour\\nGROUP BY "shopping_preference", "city_tier"\\nORDER BY "count" DESC',  delay: 2200 },
  { type: 'step',   text: '→ Executing on SQLite…',                                           delay: 4000 },
  { type: 'result', text: '✓ 9 rows returned  ·  grouped_bar chart  ·  post-processed',       delay: 4600 },
  { type: 'step',   text: '→ Rendering dashboard…',                                           delay: 5200 },
]

function TerminalDemo() {
  const [visibleSteps, setVisibleSteps] = useState([])
  const [chartVisible, setChartVisible] = useState(false)
  const [cycle, setCycle]               = useState(0)
  const containerRef = useRef(null)

  useEffect(() => {
    setVisibleSteps([])
    setChartVisible(false)
    let timers = []
    TERMINAL_STEPS.forEach((step, i) => {
      timers.push(setTimeout(() => {
        setVisibleSteps(prev => [...prev, step])
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight
        }
      }, step.delay))
    })
    timers.push(setTimeout(() => setChartVisible(true), 6000))
    // Loop
    timers.push(setTimeout(() => setCycle(c => c + 1), 9500))
    return () => timers.forEach(clearTimeout)
  }, [cycle])

  return (
    <div className={styles.terminalWrap}>
      {/* Terminal */}
      <div className={styles.terminal} ref={containerRef}>
        <div className={styles.terminalBar}>
          <span className={`${styles.dot} ${styles.dotR}`}/><span className={`${styles.dot} ${styles.dotY}`}/><span className={`${styles.dot} ${styles.dotG}`}/>
          <span className={styles.terminalTitle}>InsightFlow · pipeline</span>
        </div>
        <div className={styles.terminalBody}>
          {visibleSteps.map((step, i) => (
            <div key={i} className={styles.line}>
              {step.type === 'input' && (
                <><span className={styles.prompt}>$</span>
                <span className={styles.inputText}>"{step.text}"</span></>
              )}
              {step.type === 'step'   && <span className={styles.stepText}>{step.text}</span>}
              {step.type === 'sql'    && (
                <pre className={styles.sql}>{step.text}</pre>
              )}
              {step.type === 'result' && <span className={styles.resultText}>{step.text}</span>}
            </div>
          ))}
          {visibleSteps.length > 0 && !chartVisible && (
            <span className={styles.cursor}>▋</span>
          )}
        </div>
      </div>

      {/* Mini chart preview */}
      <div className={`${styles.chartPreview} ${chartVisible ? styles.chartVisible : ''}`}>
        <div className={styles.chartHeader}>
          <span className={styles.chartTitle}>Customer distribution by shopping preference × city tier</span>
          <Badge variant="blue">grouped_bar</Badge>
          <Badge variant="green">9 rows</Badge>
        </div>
        <div className={styles.bars}>
          {[
            { label: 'Store',  t1: 72, t2: 48, t3: 65 },
            { label: 'Online', t1: 18, t2: 12, t3: 10 },
            { label: 'Hybrid', t1:  8,  t2:  5, t3:  4 },
          ].map(d => (
            <div key={d.label} className={styles.barRow}>
              <span className={styles.barLabel}>{d.label}</span>
              <div className={styles.barGroup}>
                <div className={`${styles.bar} ${styles.bar1}`} style={{ width: `${d.t1}%` }}/>
                <div className={`${styles.bar} ${styles.bar2}`} style={{ width: `${d.t2}%` }}/>
                <div className={`${styles.bar} ${styles.bar3}`} style={{ width: `${d.t3}%` }}/>
              </div>
            </div>
          ))}
        </div>
        <div className={styles.chartLegend}>
          <span className={`${styles.leg} ${styles.leg1}`}/>Tier 1
          <span className={`${styles.leg} ${styles.leg2}`}/>Tier 2
          <span className={`${styles.leg} ${styles.leg3}`}/>Tier 3
        </div>
        <div className={styles.insight}>
          ✦ Store preference dominates across all city tiers (70–80%). Hybrid shopping is consistently rare (&lt;10%).
        </div>
      </div>
    </div>
  )
}

// ── Architecture pill strip ────────────────────────────────────────────────────
const STACK = [
  { name: 'FastAPI',       role: 'REST API',         color: '#059669' },
  { name: 'SQLite + WAL',  role: 'Query engine',     color: '#0891b2' },
  { name: 'Groq LLM',      role: 'llama-3.3-70b',    color: '#7c3aed' },
  { name: 'Post-processor','role': '8-rule validator','color': '#d97706' },
  { name: 'React 18',      role: 'Frontend',         color: '#1a56db' },
  { name: 'Recharts',      role: 'Visualisation',    color: '#be185d' },
]

// ── Stat counters ─────────────────────────────────────────────────────────────
const STATS = [
  { value: '11,789', label: 'customer records' },
  { value: '25',     label: 'columns classified' },
  { value: '8',      label: 'post-process rules' },
  { value: '<1s',    label: 'avg response time' },
]

// ── Differentiators ───────────────────────────────────────────────────────────
const DIFFS = [
  {
    tag: 'Honesty by design',
    title: 'Refuses to hallucinate',
    body: 'When a question cannot be answered with the available data, InsightFlow says so. No fabricated charts, no confident-looking lies. Most BI tools don\'t do this.',
    color: '#7c3aed',
  },
  {
    tag: 'Post-processor',
    title: 'Auto-corrects chart types',
    body: '8 validation rules run after every LLM response. Pie charts with a dominant 87% slice are automatically converted to bar charts with an explanation badge.',
    color: '#0891b2',
  },
  {
    tag: 'Alias system',
    title: 'Zero hallucinated columns',
    body: 'Every continuous column gets a standardised SQL alias in the schema context. The LLM is told exactly what to write — eliminating the "age_bucket" class of errors.',
    color: '#059669',
  },
  {
    tag: 'Read-only SQLite',
    title: 'Structurally secure',
    body: 'DROP, INSERT, UPDATE, DELETE, ATTACH, PRAGMA are blocklisted by regex. The database opens in ?mode=ro URI. No amount of prompt injection can write data.',
    color: '#d97706',
  },
]

// ── Main component ─────────────────────────────────────────────────────────────
export default function Landing() {
  const navigate   = useNavigate()
  const [loading, setLoading] = useState(false)

  async function launchDemo() {
    setLoading(true)
    try {
      await preloadDataset()
    } catch { /* best effort — dashboard handles no-dataset gracefully */ }
    navigate('/dashboard')
  }

  return (
    <div className={styles.page}>
      {/* ══ HERO ════════════════════════════════════════════════════════════════ */}
      <section className={`${styles.hero} ${styles.relative}`}>
        <div className={styles.heroInner}>
          <div className={styles.heroLeft}>
            <div className={styles.eyebrow}>
              <span className={styles.eyebrowDot}/>
              GFG Classroom × MVSR Hackathon 2026
            </div>
            <h1 className={styles.h1}>
              Plain English<br/>
              <span className={styles.h1Accent}>→ Instant Dashboard</span>
            </h1>
            <p className={styles.heroBody}>
              Type a business question. InsightFlow generates SQL, validates it, picks the right chart type, and renders an interactive BI dashboard — in under two seconds.
            </p>
            <div className={styles.heroActions}>
              <Button size="lg" variant="primary" onClick={() => launchDemo()} disabled={loading}>
                {loading ? 'Loading…' : 'Try live demo →'}
              </Button>
              <Button size="lg" variant="secondary" onClick={() => navigate('/upload')}>
                Upload your CSV
              </Button>
            </div>
            <div className={styles.stats}>
              {STATS.map(s => (
                <div key={s.label} className={styles.stat}>
                  <span className={styles.statVal}>{s.value}</span>
                  <span className={styles.statLabel}>{s.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.heroRight}>
            <TerminalDemo />
          </div>
        </div>
      </section>

      {/* ══ STACK STRIP ════════════════════════════════════════════════════════ */}
      <section className={`${styles.stackStrip} ${styles.relative}`}>
        <span className={styles.stackLabel}>Built with</span>
        {STACK.map(s => (
          <div key={s.name} className={styles.stackPill} style={{ '--pill-color': s.color }}>
            <span className={styles.stackDot}/>
            <span className={styles.stackName}>{s.name}</span>
            <span className={styles.stackRole}>{s.role}</span>
          </div>
        ))}
      </section>

      {/* ══ DIFFERENTIATORS ════════════════════════════════════════════════════ */}
      <section className={`${styles.section} ${styles.relative}`}>
        <div className={styles.sectionHead}>
          <h2 className={styles.h2}>What separates InsightFlow from a demo project</h2>
          <p className={styles.sectionSub}>Every feature below was designed to address a real failure mode in AI-powered BI tools.</p>
        </div>
        <div className={styles.grid}>
          {DIFFS.map(d => (
            <Card key={d.title} className={styles.diffCard} style={{ borderLeft: `3px solid ${d.color}` }}>
              <div className={styles.diffTag} style={{ color: d.color }}>{d.tag}</div>
              <h3 className={styles.diffTitle}>{d.title}</h3>
              <p className={styles.diffBody}>{d.body}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* ══ PIPELINE ═══════════════════════════════════════════════════════════ */}
      <section className={`${styles.section} ${styles.sectionAlt} ${styles.relative}`}>
        <div className={styles.sectionHead}>
          <h2 className={styles.h2}>The full pipeline</h2>
          <p className={styles.sectionSub}>Every query passes through 6 validated stages before a chart renders. Reliability is treated as a first-class feature.</p>
        </div>
        <div className={styles.pipelineGrid}>
          {[
            { n: '01', title: 'Schema context',   body: 'Column roles, bucket SQL, aliases, and GFG-specific notes injected into every prompt.' },
            { n: '02', title: 'LLM call (Groq)',   body: 'llama-3.3-70b generates SQL + chart spec JSON. System prompt forces raw JSON only.' },
            { n: '03', title: 'SQL validation',    body: 'Blocklist check + word-boundary regex + table name verification before execution.' },
            { n: '04', title: 'SQLite execution',  body: 'Read-only URI mode. Per-session WAL database. Results returned as typed dicts.' },
            { n: '05', title: 'Post-processor',    body: '8 rules: empty guard, row limit, pie correction, pivot, Pearson r, ambiguity flag.' },
            { n: '06', title: 'Cannot-answer gate','body': 'x_col validity, time-series detection, empty chart guard. Honest refusals, not hallucinations.' },
          ].map((s, i) => (
            <div key={s.n} className={styles.pipeStep}>
              <div className={styles.pipeNum}>{s.n}</div>
              <div className={styles.pipeContent}>
                <div className={styles.pipeTitle}>{s.title}</div>
                <div className={styles.pipeBody}>{s.body}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ══ DEMO QUERIES ═══════════════════════════════════════════════════════ */}
      <section className={`${styles.section} ${styles.relative}`}>
        <div className={styles.sectionHead}>
          <h2 className={styles.h2}>Click to run on the live dataset</h2>
          <p className={styles.sectionSub}>Pre-loaded: 11,789 customers · 25 columns · retail consumer behaviour</p>
        </div>
        <div className={styles.demoGrid}>
          {[
            { q: 'Show customer distribution by shopping preference and city tier',         tag: 'grouped_bar · 9 rows',    icon: '▦' },
            { q: 'Compare average online vs store spending by gender and city tier',        tag: 'grouped_bar · 6 rows',    icon: '▦' },
            { q: 'Show age distribution of customers by shopping preference',              tag: 'bar · age_group',         icon: '▤' },
            { q: 'Show distribution of daily internet hours by city tier',                    tag: 'bar · bucket SQL',        icon: '▤' },
            { q: 'Compare brand loyalty scores across shopping preferences',               tag: 'bar · AVG score',         icon: '▤' },
            { q: 'Show monthly online orders vs store visits by city tier',                tag: 'grouped_bar · counts',    icon: '▦' },
          ].map(d => (
            <button key={d.q} className={styles.demoBtn} onClick={() => launchDemo()} disabled={loading}>
              <span className={styles.demoIcon}>{d.icon}</span>
              <span className={styles.demoQ}>"{d.q}"</span>
              <span className={styles.demoTag}>{d.tag} →</span>
            </button>
          ))}
        </div>
      </section>

      {/* ══ FOOTER CTA ═════════════════════════════════════════════════════════ */}
      <section className={`${styles.footerCta} ${styles.relative}`}>
        <h2 className={styles.h2}>Ready to explore the data?</h2>
        <p className={styles.footerCtaSub}>
          No setup required. The dataset is pre-loaded. Ask your first question in seconds and experience the InsightFlow magic.
        </p>
        <div className={styles.footerCtaActions}>
          <Button size="lg" variant="primary" onClick={() => launchDemo()} disabled={loading}>
            {loading ? 'Loading…' : 'Open live dashboard →'}
          </Button>
          <Button size="lg" variant="secondary" onClick={() => navigate('/upload')}>
            Upload your own CSV
          </Button>
        </div>
      </section>

      <footer className={styles.footer}>
        InsightFlow · Built for GFG Classroom × MVSR Hyderabad Hackathon 2026
      </footer>
    </div>
  )
}