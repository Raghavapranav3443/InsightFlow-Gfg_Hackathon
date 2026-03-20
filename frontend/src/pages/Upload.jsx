import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadCsv, preloadDataset, getSchema } from '../utils/api'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import styles from './Upload.module.css'

const ROLE_COLORS = {
  continuous: '#3b82f6', score: '#8b5cf6', measure: '#f59e0b',
  dimension: '#10b981', id: '#6b7280', datetime: '#ef4444', text: '#94a3b8',
}

export default function Upload() {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [schema, setSchema] = useState(null)   // full schema from /schema endpoint
  const inputRef = useRef(null)
  const navigate = useNavigate()

  async function processFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Only CSV files are accepted (.csv extension required)')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('File exceeds the 5 MB limit. Please use a smaller dataset.')
      return
    }
    if (file.size === 0) {
      setError('The selected file is empty.')
      return
    }

    // Clear cached dashboard state so new dataset gets a fresh overview
    try {
      ['insightflow_last_result','insightflow_last_prompt',
       'insightflow_last_query','insightflow_overview'].forEach(k => sessionStorage.removeItem(k))
    } catch {}

    setLoading(true)
    setError(null)
    setSchema(null)

    try {
      // Upload and ingest the CSV
      await uploadCsv(file)
      // Fetch full schema (column roles, nunique, samples) for the preview table
      const s = await getSchema()
      setSchema(s)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function useSampleDataset() {
    setLoading(true)
    setError(null)
    setSchema(null)
    try {
      await preloadDataset()
      const s = await getSchema()
      setSchema(s)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) processFile(file)
  }

  function reset() {
    setSchema(null)
    setError(null)
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Upload Dataset</h1>
      <p className={styles.subtitle}>
        Upload any CSV file (up to 5 MB) to start asking natural-language questions about your data.
        Column types are detected automatically.
      </p>

      {!schema ? (
        <>
          {/* Drop zone */}
          <div
            className={`${styles.dropZone} ${dragging ? styles.dragOver : ''}`}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
          >
            <div className={styles.dropIcon}>{loading ? '⏳' : '📁'}</div>
            <h3 className={styles.dropTitle}>{loading ? 'Processing…' : 'Drop your CSV file here'}</h3>
            {!loading && (
              <>
                <p className={styles.dropText}>or click to browse · UTF-8 or latin-1 · max 5 MB</p>
                <Button
                  variant="secondary"
                  disabled={loading}
                  onClick={e => { e.stopPropagation(); inputRef.current?.click() }}
                >
                  Browse files
                </Button>
              </>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".csv"
              className={styles.fileInput}
              onChange={e => { const f = e.target.files[0]; if (f) processFile(f) }}
            />
          </div>

          <div className={styles.divider}>
            or use the pre-loaded dataset
          </div>

          <div style={{ textAlign: 'center' }}>
            <Button
              variant="secondary"
              size="lg"
              onClick={useSampleDataset}
              disabled={loading}
            >
              📊 Use GFG Dataset (11,789 rows · 25 columns)
            </Button>
          </div>

          {error && (
            <div className={styles.errorBox}>
              <strong>Error:</strong> {error}
            </div>
          )}
        </>
      ) : (
        /* ── Schema preview ── */
        <div>
          <Card className={styles.schemaCard}>
            <div className={styles.cardHeader}>
              <div>
                <div className={styles.datasetName}>{schema.dataset_name}</div>
                <div className={styles.datasetMeta}>
                  {schema.row_count.toLocaleString()} rows · {schema.columns.length} columns
                  {!schema.has_date_column && (
                    <span className={styles.warningText}>
                      ⚠ No date column (time-series queries will be declined)
                    </span>
                  )}
                </div>
              </div>
              <Badge variant="green">✓ Loaded</Badge>
            </div>

            {/* Full column preview — populated from /schema */}
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Column</th>
                    <th className={styles.th}>Type</th>
                    <th className={styles.th}>Role</th>
                    <th className={styles.th}>Unique</th>
                    <th className={styles.th}>Samples</th>
                  </tr>
                </thead>
                <tbody>
                  {schema.columns.map(col => (
                    <tr key={col.safe_name}>
                      <td className={styles.td}>
                        <div className={styles.colNameCell}>
                          <span className={styles.roleDot} style={{
                            background: ROLE_COLORS[col.role] || '#94a3b8',
                          }} />
                          {col.safe_name}
                          {col.is_ambiguous && (
                            <span title="Ambiguous — see data dictionary" style={{ color: 'var(--warning)' }}>⚠</span>
                          )}
                        </div>
                      </td>
                      <td className={`${styles.td} ${styles.typeText}`}>{col.sql_type}</td>
                      <td className={styles.td}>
                        <Badge variant={
                          col.role === 'continuous' ? 'blue'
                          : col.role === 'dimension' ? 'green'
                          : col.role === 'score' ? 'purple'
                          : 'gray'
                        }>
                          {col.role}
                        </Badge>
                      </td>
                      <td className={styles.td}>{col.nunique}</td>
                      <td className={`${styles.td} ${styles.samplesText}`}>
                        {col.samples?.slice(0, 3).join(', ') || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <div className={styles.actions}>
            <Button variant="primary" size="lg" onClick={() => navigate('/dashboard')}>
              Open Dashboard →
            </Button>
            <Button variant="ghost" onClick={reset}>
              Upload different file
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}