import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Reusable Spinner Component
 */
const Spinner = ({
  size = 'md',
  color = 'blue',
  fullScreen = false,
  message = null,
}) => {
  const sizes = {
    xs: 'w-4 h-4',
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  };

  const colors = {
    blue: 'text-blue-600',
    gray: 'text-gray-600',
    green: 'text-green-600',
    red: 'text-red-600',
    white: 'text-white',
  };

  const spinner = (
    <div className="flex flex-col items-center justify-center gap-3">
      <Loader2 className={`animate-spin ${sizes[size]} ${colors[color]}`} />
      {message && (
        <p className="text-sm text-gray-600">{message}</p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-white bg-opacity-90 z-50">
        {spinner}
      </div>
    );
  }

  return spinner;
};

export default Spinner;