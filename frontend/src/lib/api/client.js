/**
 * lib/api/client.js
 * ──────────────────────────────────────────────────────────────────────────────
 * JWT-aware API client used by all feature modules.
 *
 * IMPORTANT: This module cannot import AuthContext directly (would cause a
 * circular dependency). Instead it accepts the `apiFetch` function from
 * AuthContext as a parameter via makeClient(apiFetch).
 *
 * For the legacy session-based routes (which still work while auth is being
 * rolled out), we also export a plain `legacyFetch` that sends X-Session-ID.
 */
import { getSessionId } from '../../utils/session'

const BASE = '/api'

// ── Legacy fetch (X-Session-ID based — used until all routes are JWT-ready) ───
export async function legacyFetch(path, options = {}) {
  const sid = getSessionId()
  const res = await fetch(BASE + path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Session-ID': sid,
      ...(options.headers || {}),
    },
  })

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail || body.message || detail
    } catch {}
    throw new Error(detail)
  }
  return res.json()
}

// ── Factory: builds a typed API client given the auth-aware `apiFetch` ────────
export function makeClient(apiFetch) {

  // Shared helper — wraps apiFetch with JSON parse + error extraction
  async function call(path, options = {}) {
    const res = await apiFetch(BASE + path, options)
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const body = await res.json()
        detail = body.detail || body.message || detail
      } catch {}
      throw new Error(detail)
    }
    return res.json()
  }

  // ── Datasets ────────────────────────────────────────────────────────────────
  async function listDatasets() {
    return call('/datasets')
  }

  async function uploadDataset(file) {
    const sid = getSessionId()
    const form = new FormData()
    form.append('file', file)
    const res = await apiFetch(BASE + '/datasets', {
      method: 'POST',
      headers: { 'X-Session-ID': sid },  // multipart — no Content-Type override
      body: form,
    })
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try { const b = await res.json(); detail = b.detail || detail } catch {}
      throw new Error(detail)
    }
    return res.json()
  }

  async function deleteDataset(id) {
    return call(`/datasets/${id}`, { method: 'DELETE' })
  }

  // ── Dashboards ─────────────────────────────────────────────────────────────
  async function listDashboards() {
    return call('/dashboards')
  }

  async function saveDashboard(payload) {
    return call('/dashboards', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async function deleteDashboard(id) {
    return call(`/dashboards/${id}`, { method: 'DELETE' })
  }

  // ── History ─────────────────────────────────────────────────────────────────
  async function getHistory(datasetId) {
    const qs = datasetId ? `?dataset_id=${datasetId}` : ''
    return call(`/history${qs}`)
  }

  // ── User ────────────────────────────────────────────────────────────────────
  async function getMe() {
    return call('/me')
  }

  return {
    listDatasets,
    uploadDataset,
    deleteDataset,
    listDashboards,
    saveDashboard,
    deleteDashboard,
    getHistory,
    getMe,
  }
}
