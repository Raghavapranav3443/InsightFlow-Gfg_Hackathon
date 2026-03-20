import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import styles from './Login.module.css'

// ── Password strength meter ────────────────────────────────────────────────────
function strengthScore(pw) {
  let score = 0
  if (pw.length >= 8)  score++
  if (pw.length >= 12) score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  return score  // 0-5
}

function StrengthBar({ password }) {
  if (!password) return null
  const score = strengthScore(password)
  const labels = ['', 'Very weak', 'Weak', 'Fair', 'Good', 'Strong']
  const colors = ['', '#ef4444', '#f59e0b', '#eab308', '#22c55e', '#10b981']
  return (
    <div className={styles.strengthWrap}>
      <div className={styles.strengthBars}>
        {[1,2,3,4,5].map(i => (
          <div
            key={i}
            className={styles.strengthBar}
            style={{ background: i <= score ? colors[score] : 'var(--border)' }}
          />
        ))}
      </div>
      <span className={styles.strengthLabel} style={{ color: colors[score] }}>
        {labels[score]}
      </span>
    </div>
  )
}

// ── Register page ──────────────────────────────────────────────────────────────
export default function Register() {
  const navigate = useNavigate()
  const { register } = useAuth()

  const [email,       setEmail]       = useState('')
  const [password,    setPassword]    = useState('')
  const [confirm,     setConfirm]     = useState('')
  const [displayName, setDisplayName] = useState('')
  const [aiConsent,   setAiConsent]   = useState(false)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState(null)

  const canSubmit = email && password.length >= 8 && password === confirm && aiConsent && !loading

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    setError(null)
    setLoading(true)
    try {
      await register(email, password, displayName)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        {/* Header */}
        <div className={styles.cardHeader}>
          <div className={styles.brandIcon}>✦</div>
          <h1 className={styles.title}>Create your account</h1>
          <p className={styles.subtitle}>Start turning data into insights instantly</p>
        </div>

        {/* Form */}
        <form className={styles.form} onSubmit={handleSubmit} noValidate>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="reg-name">Display name <span className={styles.optional}>(optional)</span></label>
            <input
              id="reg-name"
              type="text"
              className={styles.input}
              placeholder="Your name"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              autoComplete="name"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="reg-email">Email address</label>
            <input
              id="reg-email"
              type="email"
              className={styles.input}
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="reg-pass">Password <span className={styles.optional}>(min 8 chars, letters + numbers)</span></label>
            <input
              id="reg-pass"
              type="password"
              className={styles.input}
              placeholder="Create a password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
            <StrengthBar password={password} />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="reg-confirm">Confirm password</label>
            <input
              id="reg-confirm"
              type="password"
              className={`${styles.input} ${confirm && confirm !== password ? styles.inputError : ''}`}
              placeholder="Repeat your password"
              value={confirm}
              onChange={e => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
            />
            {confirm && confirm !== password && (
              <span className={styles.fieldError}>Passwords don't match</span>
            )}
          </div>

          {/* AI data consent */}
          <label className={styles.consentRow}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={aiConsent}
              onChange={e => setAiConsent(e.target.checked)}
              required
            />
            <span className={styles.consentText}>
              I understand that query results may be sent to an AI provider (Groq / Gemini) to generate chart insights. No personal data is stored by the AI.
            </span>
          </label>

          {error && (
            <div className={styles.errorBanner}>
              <span className={styles.errorIcon}>⚠</span> {error}
            </div>
          )}

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={!canSubmit}
          >
            {loading ? (
              <><span className={styles.spinner} /> Creating account…</>
            ) : 'Create account →'}
          </button>
        </form>

        <div className={styles.footer}>
          Already have an account?{' '}
          <Link to="/login" className={styles.link}>Sign in</Link>
        </div>
      </div>
    </div>
  )
}
