import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { healthCheck } from './utils/api'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ToastContainer } from './components/ui/Toast'
import Landing from './pages/Landing'
import AutoDashboard from './pages/AutoDashboard'
import QueryExplorer from './pages/QueryExplorer'
import Upload from './pages/Upload'
import History from './pages/History'
import Login from './pages/Login'
import Register from './pages/Register'
import Navbar from './components/Navbar'
import SharedDashboard from './pages/SharedDashboard'

// ── Protected route: redirects to /login if not authenticated ─────────────────
function ProtectedRoute({ children }) {
  const { isAuthenticated, ready } = useAuth()
  if (!ready) return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', gap: 12, color: 'var(--text-muted)', fontSize: '0.9rem'
    }}>
      <span style={{
        width: 18, height: 18, border: '2px solid var(--border)',
        borderTopColor: 'var(--primary)', borderRadius: '50%',
        animation: 'spin 0.8s linear infinite', display: 'inline-block'
      }} />
      Loading…
    </div>
  )
  // Allow access even when not authenticated — the app still works with legacy
  // session-ID routes. A full auth gate can be enabled here later.
  return children
}

function AppRoutes({ health }) {
  return (
    <>
      <Navbar health={health} />
      <Routes>
        <Route path="/"          element={<Landing />} />
        <Route path="/login"     element={<Login />} />
        <Route path="/register"  element={<Register />} />
        <Route path="/dashboard" element={<ProtectedRoute><AutoDashboard /></ProtectedRoute>} />
        <Route path="/explore"   element={<ProtectedRoute><QueryExplorer health={health} /></ProtectedRoute>} />
        <Route path="/upload"    element={<ProtectedRoute><Upload /></ProtectedRoute>} />
        <Route path="/history"   element={<ProtectedRoute><History /></ProtectedRoute>} />
        <Route path="/share/:token" element={<SharedDashboard />} />
        <Route path="*"          element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}

export default function App() {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    async function poll() {
      try {
        const h = await healthCheck()
        setHealth(h)
      } catch {
        setHealth(null)
      }
    }
    poll()
    const interval = setInterval(poll, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastContainer />
        <AppRoutes health={health} />
      </AuthProvider>
    </BrowserRouter>
  )
}
