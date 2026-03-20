import React from 'react';
import styles from './Button.module.css';

export default function Button({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  icon = false,
  className = '',
  ...props 
}) {
  const variantClass = styles[`btn-${variant}`] || styles['btn-primary'];
  const sizeClass = size !== 'md' ? styles[`btn-${size}`] : '';
  const iconClass = icon ? styles['btn-icon'] : '';

  return (
    <button 
      className={`${styles.btn} ${variantClass} ${sizeClass} ${iconClass} ${className}`.trim()} 
      {...props}
    >
      {children}
    </button>
  );
}
