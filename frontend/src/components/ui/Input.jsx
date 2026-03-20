/**
 * Input.jsx — Styled text input with label, helper text, and error state.
 * Usage:
 *   <Input label="Email" type="email" value={v} onChange={e => setV(e.target.value)} />
 *   <Input label="Name" error="Required" />
 */
import styles from './Input.module.css'

export default function Input({
  label,
  error,
  hint,
  id,
  className = '',
  type = 'text',
  ...props
}) {
  const inputId = id || `input-${label?.replace(/\s+/g, '-').toLowerCase()}-${Math.random().toString(36).slice(2,6)}`
  return (
    <div className={`${styles.field} ${className}`}>
      {label && (
        <label className={styles.label} htmlFor={inputId}>{label}</label>
      )}
      <input
        id={inputId}
        type={type}
        className={`${styles.input} ${error ? styles.hasError : ''}`}
        aria-invalid={!!error}
        aria-describedby={error ? `${inputId}-err` : hint ? `${inputId}-hint` : undefined}
        {...props}
      />
      {error && <span id={`${inputId}-err`} className={styles.error}>{error}</span>}
      {!error && hint && <span id={`${inputId}-hint`} className={styles.hint}>{hint}</span>}
    </div>
  )
}
