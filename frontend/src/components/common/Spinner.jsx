import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Enhanced Spinner Component
 */
const Spinner = ({ 
  size = 'md', 
  message = null, 
  fullScreen = false,
  color = 'blue'
}) => {
  const sizeClasses = {
    xs: 'w-4 h-4',
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  };

  const colorClasses = {
    blue: 'text-blue-600',
    green: 'text-green-600',
    purple: 'text-purple-600',
    red: 'text-red-600',
    gray: 'text-gray-600',
  };

  const spinner = (
    <div className="flex flex-col items-center justify-center gap-4">
      <div className="relative">
        <Loader2 
          className={`${sizeClasses[size]} ${colorClasses[color]} animate-spin`} 
        />
        {/* Pulsing background circle */}
        <div className={`absolute inset-0 ${colorClasses[color]} opacity-20 rounded-full animate-ping`}></div>
      </div>
      {message && (
        <p className="text-sm font-medium text-gray-600 animate-pulse">
          {message}
        </p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-white bg-opacity-90 backdrop-blur-sm flex items-center justify-center z-50">
        {spinner}
      </div>
    );
  }

  return spinner;
};

export default Spinner;