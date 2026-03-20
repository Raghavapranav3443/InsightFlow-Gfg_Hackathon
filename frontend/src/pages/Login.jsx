import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import styles from './Login.module.css'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!email || !password || loading) return
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
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
          <h1 className={styles.title}>Sign in to InsightFlow</h1>
          <p className={styles.subtitle}>Natural language analytics for your data</p>
        </div>

        {/* Form */}
        <form className={styles.form} onSubmit={handleSubmit} noValidate>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="login-email">Email address</label>
            <input
              id="login-email"
              type="email"
              className={styles.input}
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoComplete="email"
              autoFocus
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="login-pass">Password</label>
            <input
              id="login-pass"
              type="password"
              className={styles.input}
              placeholder="Your password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div className={styles.errorBanner}>
              <span className={styles.errorIcon}>⚠</span> {error}
            </div>
          )}

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={!email || !password || loading}
          >
            {loading ? (
              <><span className={styles.spinner} /> Signing in…</>
            ) : 'Sign in →'}
          </button>
        </form>

        {/* Divider for future Google OAuth */}
        <div className={styles.divider}><span>or continue as guest</span></div>

        <button
          className={styles.guestBtn}
          onClick={() => navigate('/')}
        >
          Try the live demo without signing in
        </button>

        <div className={styles.footer}>
          No account yet?{' '}
          <Link to="/register" className={styles.link}>Create one free</Link>
        </div>
      </div>
    </div>
  )
}
