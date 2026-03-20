/**
 * zustand/useDashboardStore.js
 * ──────────────────────────────────────────────────────────────────────────────
 * Manages query result, history entries, and saved dashboards.
 */
import { create } from 'zustand'

export const useDashboardStore = create((set, get) => ({
  // Current query result (replaces sessionStorage usage)
  result:      null,
  lastPrompt:  '',

  // Sidebar history (recent queries)
  history:     [],   // [{ id, prompt, result, timestamp }]

  // Saved dashboards fetched from GET /dashboards
  saved:       [],   // [{ id, name, data, created_at }]

  // Actions
  setResult(result, prompt) {
    const entry = { id: Date.now(), prompt, result, timestamp: new Date().toISOString() }
    set(state => ({
      result,
      lastPrompt: prompt,
      history: [entry, ...state.history].slice(0, 20), // keep last 20
    }))
  },

  clearResult() {
    set({ result: null, lastPrompt: '' })
  },

  setSaved(saved) {
    set({ saved })
  },

  addSaved(dashboard) {
    set(state => ({ saved: [dashboard, ...state.saved] }))
  },

  removeSaved(id) {
    set(state => ({ saved: state.saved.filter(d => d.id !== id) }))
  },

  restoreFromHistory(entry) {
    set({ result: entry.result, lastPrompt: entry.prompt })
  },
}))
