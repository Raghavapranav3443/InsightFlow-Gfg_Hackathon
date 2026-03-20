import React from 'react';
import styles from './Badge.module.css';

export default function Badge({ 
  children, 
  variant = 'blue', 
  className = '',
  ...props 
}) {
  const variantClass = styles[`badge-${variant}`] || styles['badge-blue'];

  return (
    <span 
      className={`${styles.badge} ${variantClass} ${className}`.trim()} 
      {...props}
    >
      {children}
    </span>
  );
}
