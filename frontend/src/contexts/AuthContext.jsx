/**
 * AuthContext.jsx
 * ──────────────────────────────────────────────────────────────────────────────
 * Provides JWT-based auth state to the entire app.
 *
 * Design decisions:
 *  - Access token stored IN-MEMORY only (not localStorage) — XSS-safe
 *  - Refresh token lives in an httpOnly cookie — JS cannot touch it
 *  - On mount: silently try POST /auth/refresh to restore session from cookie
 *  - All API calls via apiFetch() — auto-retries with fresh token on 401
 */
import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'

const AuthContext = createContext(null)

const BASE = '/auth'

// ── Low-level fetch helpers ────────────────────────────────────────────────────

async function authPost(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    credentials: 'include',          // needed so httpOnly cookie is sent/received
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || data.message || `HTTP ${res.status}`)
  return data
}

// ── Provider ──────────────────────────────────────────────────────────────────

export function AuthProvider({ children }) {
  // user = { user_id, email, display_name } | null
  const [user,  setUser]  = useState(null)
  const [token, setToken] = useState(null)   // in-memory access token
  const [ready, setReady] = useState(false)  // true once initial refresh attempt done

  const refreshTimerRef = useRef(null)

  // Schedule an auto-refresh 60s before the token expires (token is 15 min)
  const scheduleRefresh = useCallback((intervalMs = 14 * 60 * 1000) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    refreshTimerRef.current = setTimeout(async () => {
      try {
        const data = await authPost('/refresh')
        setToken(data.access_token)
        setUser({ user_id: data.user_id, email: data.email, display_name: data.display_name })
        scheduleRefresh()
      } catch {
        // Refresh failed — session expired, force logout
        setToken(null)
        setUser(null)
      }
    }, intervalMs)
  }, [])

  // On mount: try silent refresh from httpOnly cookie
  useEffect(() => {
    let cancelled = false
    async function silentRefresh() {
      try {
        const data = await authPost('/refresh')
        if (cancelled) return
        setToken(data.access_token)
        setUser({ user_id: data.user_id, email: data.email, display_name: data.display_name })
        scheduleRefresh()
      } catch {
        // No valid session — that's fine, user will land on login page
      } finally {
        if (!cancelled) setReady(true)
      }
    }
    silentRefresh()
    return () => {
      cancelled = true
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    }
  }, [scheduleRefresh])

  // ── Public actions ─────────────────────────────────────────────────────────

  // Use a ref for the token so apiFetch maintains referential stability
  // across background token refreshes, preventing unnecessary downstream re-renders.
  const tokenRef = useRef(token)
  tokenRef.current = token

  const login = useCallback(async (email, password) => {
    const data = await authPost('/login', { email, password })
    setToken(data.access_token)
    setUser({ user_id: data.user_id, email: data.email, display_name: data.display_name })
    scheduleRefresh()
    return data
  }, [scheduleRefresh])

  const register = useCallback(async (email, password, display_name = '') => {
    const data = await authPost('/register', { email, password, display_name })
    setToken(data.access_token)
    setUser({ user_id: data.user_id, email: data.email, display_name: data.display_name })
    scheduleRefresh()
    return data
  }, [scheduleRefresh])

  const logout = useCallback(async () => {
    try { await authPost('/logout') } catch { /* best effort */ }
    setToken(null)
    setUser(null)
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
  }, [])

  // ── apiFetch: JWT-aware fetch for all API calls ────────────────────────────
  // Returns a function that callers use instead of raw fetch.
  // Auto-refreshes token once on 401.
  const apiFetch = useCallback(async (url, options = {}) => {
    const doFetch = async (t) => {
      return fetch(url, {
        ...options,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(t ? { Authorization: `Bearer ${t}` } : {}),
          ...(options.headers || {}),
        },
      })
    }

    let currentToken = tokenRef.current
    let res = await doFetch(currentToken)

    if (res.status === 401 && currentToken) {
      // Try one silent refresh
      try {
        const data = await authPost('/refresh')
        const newToken = data.access_token
        setToken(newToken)
        setUser({ user_id: data.user_id, email: data.email, display_name: data.display_name })
        scheduleRefresh()
        res = await doFetch(newToken)
      } catch {
        setToken(null)
        setUser(null)
        throw new Error('Session expired — please log in again.')
      }
    }

    return res
  }, [scheduleRefresh])

  const value = { user, token, ready, login, logout, register, apiFetch, isAuthenticated: !!user }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
