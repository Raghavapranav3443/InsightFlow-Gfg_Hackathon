import React from 'react';
import styles from './Card.module.css';

export default function Card({ 
  children, 
  size = 'md', 
  className = '',
  ...props 
}) {
  const sizeClass = size !== 'md' ? styles[`card-${size}`] : '';

  return (
    <div 
      className={`${styles.card} ${sizeClass} ${className}`.trim()} 
      {...props}
    >
      {children}
    </div>
  );
}
