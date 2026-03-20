/**
 * Toast.jsx — Notification toasts that auto-dismiss.
 * Usage (via hook):
 *   const { toast } = useToast()
 *   toast.success('Dashboard saved!')
 *   toast.error('Failed to save')
 *   toast.info('Processing…')
 *
 * Mount <ToastContainer /> once at the app root (inside App.jsx or index.jsx).
 */
import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useToastStore } from './useToast'
import styles from './Toast.module.css'

const ICONS = {
  success: '✓',
  error:   '✕',
  info:    'ℹ',
  warning: '⚠',
}

function Toast({ id, type = 'info', message, onDismiss }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(id), 4000)
    return () => clearTimeout(timer)
  }, [id, onDismiss])

  return (
    <div className={`${styles.toast} ${styles[type]}`} role="alert" aria-live="polite">
      <span className={styles.icon}>{ICONS[type]}</span>
      <span className={styles.message}>{message}</span>
      <button className={styles.dismiss} onClick={() => onDismiss(id)} aria-label="Dismiss">✕</button>
    </div>
  )
}

/** Mount once in App.jsx */
export function ToastContainer() {
  const { toasts, dismiss } = useToastStore()
  if (!toasts.length) return null
  return createPortal(
    <div className={styles.container} aria-label="Notifications">
      {toasts.map(t => (
        <Toast key={t.id} {...t} onDismiss={dismiss} />
      ))}
    </div>,
    document.body
  )
}
