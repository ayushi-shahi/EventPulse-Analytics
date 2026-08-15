import React, { forwardRef } from 'react';
import { AlertCircle } from 'lucide-react';

/**
 * Reusable Input Component
 */
const Input = forwardRef(({
  label,
  type = 'text',
  placeholder = '',
  value,
  onChange,
  onBlur,
  error = null,
  helperText = null,
  required = false,
  disabled = false,
  icon: Icon = null,
  iconPosition = 'left',
  fullWidth = true,
  className = '',
  ...props
}, ref) => {
  const hasError = !!error;

  const baseInputStyles = 'block px-4 py-2.5 text-sm bg-ink-900 border rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-0 disabled:bg-ink-800 disabled:cursor-not-allowed';
  
  const borderStyles = hasError
    ? 'border-bad/40 focus:border-bad focus:ring-bad'
    : 'border-ink-600 focus:border-brand-500 focus:ring-brand-500';

  const widthClass = fullWidth ? 'w-full' : '';

  const iconPaddingLeft = Icon && iconPosition === 'left' ? 'pl-10' : '';
  const iconPaddingRight = Icon && iconPosition === 'right' ? 'pr-10' : '';

  return (
    <div className={`${fullWidth ? 'w-full' : ''}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-300 mb-1.5">
          {label}
          {required && <span className="text-bad ml-1">*</span>}
        </label>
      )}

      <div className="relative">
        {Icon && iconPosition === 'left' && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Icon className="h-5 w-5 text-gray-500" />
          </div>
        )}

        <input
          ref={ref}
          type={type}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          placeholder={placeholder}
          required={required}
          disabled={disabled}
          className={`${baseInputStyles} ${borderStyles} ${widthClass} ${iconPaddingLeft} ${iconPaddingRight} ${className}`}
          {...props}
        />

        {Icon && iconPosition === 'right' && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <Icon className="h-5 w-5 text-gray-500" />
          </div>
        )}

        {hasError && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <AlertCircle className="h-5 w-5 text-bad" />
          </div>
        )}
      </div>

      {hasError && (
        <p className="mt-1.5 text-sm text-bad">{error}</p>
      )}

      {!hasError && helperText && (
        <p className="mt-1.5 text-sm text-gray-500">{helperText}</p>
      )}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;