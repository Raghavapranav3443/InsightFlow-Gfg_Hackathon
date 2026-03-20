/**
 * Textarea.jsx — Styled resizable textarea with label, character count, error.
 * Usage:
 *   <Textarea label="Notes" rows={4} maxLength={500} value={v} onChange={...} />
 */
import styles from './Input.module.css'  // shares same CSS module as Input

export default function Textarea({
  label,
  error,
  hint,
  id,
  className = '',
  maxLength,
  value = '',
  ...props
}) {
  const inputId = id || `textarea-${label?.replace(/\s+/g, '-').toLowerCase()}-${Math.random().toString(36).slice(2,6)}`
  return (
    <div className={`${styles.field} ${className}`}>
      {label && (
        <div className={styles.labelRow}>
          <label className={styles.label} htmlFor={inputId}>{label}</label>
          {maxLength && (
            <span className={styles.charCount}>{String(value).length}/{maxLength}</span>
          )}
        </div>
      )}
      <textarea
        id={inputId}
        className={`${styles.input} ${styles.textarea} ${error ? styles.hasError : ''}`}
        maxLength={maxLength}
        value={value}
        aria-invalid={!!error}
        aria-describedby={error ? `${inputId}-err` : hint ? `${inputId}-hint` : undefined}
        {...props}
      />
      {error && <span id={`${inputId}-err`} className={styles.error}>{error}</span>}
      {!error && hint && <span id={`${inputId}-hint`} className={styles.hint}>{hint}</span>}
    </div>
  )
}
