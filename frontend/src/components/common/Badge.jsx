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
    default: 'bg-gray-100 text-gray-800',
    primary: 'bg-blue-100 text-blue-800',
    success: 'bg-green-100 text-green-800',
    danger: 'bg-red-100 text-red-800',
    warning: 'bg-yellow-100 text-yellow-800',
    info: 'bg-cyan-100 text-cyan-800',
    purple: 'bg-purple-100 text-purple-800',
    pink: 'bg-pink-100 text-pink-800',
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