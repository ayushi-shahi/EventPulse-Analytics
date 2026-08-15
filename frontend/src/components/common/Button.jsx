import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Reusable Button Component
 */
const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon: Icon = null,
  iconPosition = 'left',
  fullWidth = false,
  onClick,
  type = 'button',
  className = '',
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-brand-600 hover:bg-brand-500 text-white focus:ring-brand-500 shadow-sm hover:shadow-md',
    secondary: 'bg-gray-600 hover:bg-ink-700 text-white focus:ring-ink-600 shadow-sm',
    success: 'bg-ok hover:bg-ok/90 text-white focus:ring-ok shadow-sm',
    danger: 'bg-bad hover:bg-bad/90 text-white focus:ring-bad shadow-sm',
    warning: 'bg-warn hover:bg-warn/90 text-white focus:ring-warn shadow-sm',
    outline: 'bg-transparent border-2 border-brand-500 text-brand-400 hover:bg-brand-600/15 focus:ring-brand-500',
    ghost: 'bg-transparent hover:bg-ink-800 text-gray-300 focus:ring-ink-600',
    link: 'bg-transparent text-brand-400 hover:text-brand-300 hover:underline focus:ring-brand-500',
  };

  const sizes = {
    xs: 'px-2.5 py-1.5 text-xs',
    sm: 'px-3 py-2 text-sm',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-5 py-3 text-base',
    xl: 'px-6 py-3.5 text-lg',
  };

  const iconSizes = {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
    xl: 'w-6 h-6',
  };

  const widthClass = fullWidth ? 'w-full' : '';

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${widthClass} ${className}`}
      {...props}
    >
      {loading && (
        <Loader2 className={`animate-spin ${iconSizes[size]} ${iconPosition === 'left' ? 'mr-2' : 'ml-2'}`} />
      )}
      
      {!loading && Icon && iconPosition === 'left' && (
        <Icon className={`${iconSizes[size]} mr-2`} />
      )}
      
      {children}
      
      {!loading && Icon && iconPosition === 'right' && (
        <Icon className={`${iconSizes[size]} ml-2`} />
      )}
    </button>
  );
};

export default Button;