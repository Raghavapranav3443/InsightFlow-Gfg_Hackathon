/**
 * useToast.js — Lightweight toast store using vanilla JS (no Zustand dependency).
 * Also exposes a convenience hook `useToast()` for components.
 *
 * Usage:
 *   import { useToast } from './useToast'
 *   const { toast } = useToast()
 *   toast.success('Saved!')
 */
import { useState, useCallback, useEffect } from 'react'

// ── Singleton store (event emitter pattern, no external deps) ─────────────────
let _toasts = []
let _listeners = []
let _nextId = 1

function notify() {
  _listeners.forEach(fn => fn([..._toasts]))
}

export const toastStore = {
  add(type, message) {
    const id = _nextId++
    _toasts = [..._toasts, { id, type, message }]
    notify()
    return id
  },
  dismiss(id) {
    _toasts = _toasts.filter(t => t.id !== id)
    notify()
  },
  subscribe(fn) {
    _listeners.push(fn)
    return () => { _listeners = _listeners.filter(l => l !== fn) }
  },
}

// ── Store hook used by ToastContainer ────────────────────────────────────────
export function useToastStore() {
  const [toasts, setToasts] = useState(_toasts)
  useEffect(() => toastStore.subscribe(setToasts), [])
  const dismiss = useCallback(id => toastStore.dismiss(id), [])
  return { toasts, dismiss }
}

// ── Public hook for components ────────────────────────────────────────────────
export function useToast() {
  const toast = {
    success: (msg) => toastStore.add('success', msg),
    error:   (msg) => toastStore.add('error',   msg),
    info:    (msg) => toastStore.add('info',    msg),
    warning: (msg) => toastStore.add('warning', msg),
  }
  return { toast }
}
