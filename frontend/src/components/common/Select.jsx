import React, { forwardRef } from 'react';
import { ChevronDown } from 'lucide-react';

/**
 * Reusable Select Component
 */
const Select = forwardRef(({
  label,
  value,
  onChange,
  options = [],
  placeholder = 'Select an option',
  error = null,
  helperText = null,
  required = false,
  disabled = false,
  fullWidth = true,
  className = '',
  ...props
}, ref) => {
  const hasError = !!error;

  const baseSelectStyles = 'block px-4 py-2.5 pr-10 text-sm bg-white border rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-0 disabled:bg-gray-100 disabled:cursor-not-allowed appearance-none';
  
  const borderStyles = hasError
    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
    : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500';

  const widthClass = fullWidth ? 'w-full' : '';

  return (
    <div className={`${fullWidth ? 'w-full' : ''}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}

      <div className="relative">
        <select
          ref={ref}
          value={value}
          onChange={onChange}
          required={required}
          disabled={disabled}
          className={`${baseSelectStyles} ${borderStyles} ${widthClass} ${className}`}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
          <ChevronDown className="h-5 w-5 text-gray-400" />
        </div>
      </div>

      {hasError && (
        <p className="mt-1.5 text-sm text-red-600">{error}</p>
      )}

      {!hasError && helperText && (
        <p className="mt-1.5 text-sm text-gray-500">{helperText}</p>
      )}
    </div>
  );
});

Select.displayName = 'Select';

export default Select;