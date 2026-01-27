import React from 'react';

/**
 * Reusable Card Component
 */
const Card = ({
  children,
  title = null,
  subtitle = null,
  actions = null,
  padding = true,
  hover = false,
  className = '',
  headerClassName = '',
  bodyClassName = '',
}) => {
  const baseStyles = 'bg-white rounded-lg shadow-sm border border-gray-200';
  const hoverStyles = hover ? 'hover:shadow-md transition-shadow duration-200' : '';

  return (
    <div className={`${baseStyles} ${hoverStyles} ${className}`}>
      {(title || subtitle || actions) && (
        <div className={`px-6 py-4 border-b border-gray-200 ${headerClassName}`}>
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
              )}
              {subtitle && (
                <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
              )}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
          </div>
        </div>
      )}

      <div className={`${padding ? 'p-6' : ''} ${bodyClassName}`}>
        {children}
      </div>
    </div>
  );
};

export default Card;