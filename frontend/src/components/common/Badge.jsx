import React from 'react';

/**
 * Reusable Badge Component
 */
const Badge = ({
  children,
  variant = 'default',
  size = 'md',
  rounded = true,
  className = '',
}) => {
  const baseStyles = 'inline-flex items-center font-medium';

  const variants = {
    default: 'bg-ink-800 text-gray-200',
    primary: 'bg-brand-600/20 text-brand-300',
    success: 'bg-ok/20 text-ok',
    danger: 'bg-bad/20 text-bad',
    warning: 'bg-warn/20 text-warn',
    info: 'bg-viz-2/20 text-viz-2',
    purple: 'bg-viz-6/20 text-viz-6',
    pink: 'bg-viz-5/20 text-viz-5',
  };

  const sizes = {
    xs: 'px-2 py-0.5 text-xs',
    sm: 'px-2.5 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  };

  const roundedClass = rounded ? 'rounded-full' : 'rounded';

  return (
    <span className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${roundedClass} ${className}`}>
      {children}
    </span>
  );
};

export default Badge;