/**
 * Toggle.jsx — Accessible on/off toggle switch.
 * Usage:
 *   <Toggle checked={enabled} onChange={setEnabled} label="Auto-refresh" />
 */
import styles from './Toggle.module.css'

export default function Toggle({ checked, onChange, label, disabled = false, id }) {
  const toggleId = id || `toggle-${label?.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <label className={`${styles.wrap} ${disabled ? styles.disabled : ''}`} htmlFor={toggleId}>
      <input
        id={toggleId}
        type="checkbox"
        className={styles.input}
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        disabled={disabled}
        role="switch"
        aria-checked={checked}
      />
      <span className={styles.track}>
        <span className={styles.thumb} />
      </span>
      {label && <span className={styles.label}>{label}</span>}
    </label>
  )
}
