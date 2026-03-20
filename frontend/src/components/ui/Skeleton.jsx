/**
 * Skeleton.jsx — Animated shimmer placeholder for loading states.
 * Usage:
 *   <Skeleton width="60%" height={16} />
 *   <Skeleton variant="chart" />
 *   <Skeleton variant="card" />
 */
import styles from './Skeleton.module.css'

const VARIANTS = {
  text:    { height: 14, width: '100%', borderRadius: 4 },
  title:   { height: 22, width: '55%',  borderRadius: 4 },
  avatar:  { height: 36, width: 36,     borderRadius: '50%' },
  chart:   { height: 240, width: '100%', borderRadius: 8 },
  card:    { height: 120, width: '100%', borderRadius: 12 },
  button:  { height: 36, width: 100,    borderRadius: 8 },
}

export default function Skeleton({ variant = 'text', width, height, style, className = '' }) {
  const base = VARIANTS[variant] || VARIANTS.text
  return (
    <div
      className={`${styles.skeleton} ${className}`}
      style={{
        width:  width  ?? base.width,
        height: height ?? base.height,
        borderRadius: base.borderRadius,
        ...style,
      }}
      aria-hidden="true"
    />
  )
}

/** Convenience: stacked block of skeleton text lines */
export function SkeletonBlock({ lines = 3, gap = 8 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap }}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} variant="text" width={i === lines - 1 ? '70%' : '100%'} />
      ))}
    </div>
  )
}
