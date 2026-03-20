/**
 * Spinner.jsx — Lightweight CSS spinner.
 * Usage:
 *   <Spinner />                 // default size
 *   <Spinner size={24} />       // custom px
 *   <Spinner color="#fff" />    // override colour
 *   <Spinner label="Loading…"/> // with accessible label
 */
import styles from './Spinner.module.css'

export default function Spinner({ size = 20, color, label, className = '' }) {
  return (
    <span
      className={`${styles.spinner} ${className}`}
      style={{
        width:  size,
        height: size,
        ...(color ? { borderTopColor: color } : {}),
      }}
      role="status"
      aria-label={label || 'Loading'}
    />
  )
}
