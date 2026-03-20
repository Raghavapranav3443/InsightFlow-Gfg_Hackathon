export const colors = {
  // Surface colors for backgrounds
  surface: {
    0: 'var(--surface-0)',     // Main background
    50: 'var(--surface-50)',   // Card background
    100: 'var(--surface-100)', // Hover states
    200: 'var(--surface-200)', // Borders
    300: 'var(--surface-300)', // Subtle borders
  },
  
  // Primary brand color
  primary: {
    DEFAULT: 'var(--primary)',
    hover: 'var(--primary-hover)',
    active: 'var(--primary-active)',
    muted: 'var(--primary-muted)',
  },

  // Text colors
  text: {
    DEFAULT: 'var(--text-main)', // Primary text
    muted: 'var(--text-muted)',  // Secondary text
    inverse: 'var(--text-inverse)', // Text on primary background
  },

  // State colors
  danger: {
    DEFAULT: 'var(--danger)',
    hover: 'var(--danger-hover)',
    muted: 'var(--danger-muted)',
  },
  success: {
    DEFAULT: 'var(--success)',
    muted: 'var(--success-muted)',
  },
  warning: {
    DEFAULT: 'var(--warning)',
    muted: 'var(--warning-muted)',
  }
};
