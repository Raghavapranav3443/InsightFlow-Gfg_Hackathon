/**
 * useQueryStream.js
 * ──────────────────────────────────────────────────────────────────────────────
 * React hook that manages an SSE connection to POST /pipeline/query.
 *
 * Event sequence from backend:
 *   init → stage1_start → stage1_done → sql_exec_start →
 *   stage2_start (per chart) → sql_exec_done → insight_start →
 *   insight_done → complete
 *   error | clarify (terminal events)
 *
 * Falls back to legacy POST /api/query (JSON) when user is not authenticated
 * (i.e. guest mode with session-ID).
 */
import { useState, useCallback, useRef } from 'react'
import { getSessionId } from '../utils/session'

// Maps raw SSE event names to human-readable step labels
const EVENT_LABELS = {
  init:          'Preparing query…',
  stage1_start:  'Building SQL with AI…',
  stage1_done:   'SQL generated ✓',
  sql_exec_start:'Executing SQL safely…',
  stage2_start:  'Inferring visualization…',
  sql_exec_done: 'Data fetched ✓',
  insight_start: 'Generating insights…',
  insight_done:  'Insights ready ✓',
  complete:      'Done',
}

// How many steps total (for progress bar %)
const TOTAL_STEPS = Object.keys(EVENT_LABELS).length

function stepIndex(event) {
  return Object.keys(EVENT_LABELS).indexOf(event)
}

export function useQueryStream({ token, datasetId }) {
  const [status,      setStatus]      = useState('idle')   // idle | streaming | done | error
  const [stepLabel,   setStepLabel]   = useState('')
  const [stepPct,     setStepPct]     = useState(0)
  const [sqlPreview,  setSqlPreview]  = useState(null)     // SQL string shown mid-stream
  const [result,      setResult]      = useState(null)     // final complete payload
  const [error,       setError]       = useState(null)
  const [clarify,     setClarify]     = useState(null)     // clarification prompt string
  const abortRef = useRef(null)

  const reset = useCallback(() => {
    if (abortRef.current) abortRef.current.abort()
    setStatus('idle')
    setStepLabel('')
    setStepPct(0)
    setSqlPreview(null)
    setResult(null)
    setError(null)
    setClarify(null)
  }, [])

  const run = useCallback(async (prompt) => {
    if (!prompt?.trim()) return
    reset()
    setStatus('streaming')
    setStepLabel('Connecting…')

    // ── Authenticated path: SSE via /pipeline/query ───────────────────────────
    if (token && datasetId) {
      const controller = new AbortController()
      abortRef.current = controller

      try {
        const res = await fetch('/pipeline/query', {
          method: 'POST',
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ dataset_id: datasetId, prompt }),
        })

        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.detail || `HTTP ${res.status}`)
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() // keep incomplete line

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const payload = JSON.parse(line.slice(6))
              const evt = payload.event

              // Update step label + progress
              if (EVENT_LABELS[evt]) {
                const idx = stepIndex(evt)
                setStepLabel(EVENT_LABELS[evt])
                setStepPct(Math.round(((idx + 1) / TOTAL_STEPS) * 100))
              }

              // Show SQL preview when stage1 is done
              if (evt === 'stage1_done' && payload.sql) {
                setSqlPreview(payload.sql)
              }

              // Terminal events
              if (evt === 'complete') {
                setResult(payload)
                setStatus('done')
                setStepPct(100)
                return
              }
              if (evt === 'error') {
                setError(payload.message || 'An error occurred.')
                setStatus('error')
                return
              }
              if (evt === 'clarify') {
                setClarify(payload.message)
                setStatus('done')
                return
              }
            } catch { /* malformed JSON — skip */ }
          }
        }
      } catch (err) {
        if (err.name === 'AbortError') return
        // SSE path failed for an authenticated user. Do not fall back to legacy.
        console.error('[useQueryStream] SSE failed:', err.message)
        setError(err.message || 'Connection failed.')
        setStatus('error')
        return
      }
    }

    // ── Guest / fallback path: legacy POST /api/query (JSON) ─────────────────
    try {
      setStepLabel('Analysing with AI…')
      const sid = getSessionId()
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sid,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ prompt }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || body.message || `HTTP ${res.status}`)
      }
      const data = await res.json()

      if (data.cannot_answer) {
        setError(data.reason || 'Cannot answer this question.')
        setStatus('error')
        return
      }
      if (data.clarification_needed) {
        setClarify(data.clarification_prompt)
        setStatus('done')
        return
      }

      setResult(data)
      setStatus('done')
      setStepPct(100)
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }, [token, datasetId, reset])

  const abort = useCallback(() => {
    if (abortRef.current) abortRef.current.abort()
    setStatus('idle')
    setStepLabel('')
  }, [])

  return {
    run,
    abort,
    reset,
    status,      // 'idle' | 'streaming' | 'done' | 'error'
    stepLabel,   // e.g. "Building SQL with AI…"
    stepPct,     // 0-100
    sqlPreview,  // SQL string or null
    result,      // final result payload or null
    error,       // error string or null
    clarify,     // clarification prompt or null
    isStreaming: status === 'streaming',
    isDone:      status === 'done',
    isError:     status === 'error',
  }
}
