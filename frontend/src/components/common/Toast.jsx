import React, { useEffect } from 'react';
import { X, CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-react';

/**
 * Individual Toast Notification Component
 */
const Toast = ({ id, message, type = 'info', onClose, duration = 5000 }) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose(id);
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [id, duration, onClose]);

  const types = {
    success: {
      bg: 'bg-green-50 border-green-500',
      text: 'text-green-800',
      icon: CheckCircle,
      iconColor: 'text-green-500',
    },
    error: {
      bg: 'bg-red-50 border-red-500',
      text: 'text-red-800',
      icon: XCircle,
      iconColor: 'text-red-500',
    },
    warning: {
      bg: 'bg-yellow-50 border-yellow-500',
      text: 'text-yellow-800',
      icon: AlertTriangle,
      iconColor: 'text-yellow-500',
    },
    info: {
      bg: 'bg-blue-50 border-blue-500',
      text: 'text-blue-800',
      icon: Info,
      iconColor: 'text-blue-500',
    },
  };

  const config = types[type];
  const Icon = config.icon;

  return (
    <div className={`flex items-start gap-3 p-4 rounded-lg border-l-4 shadow-lg ${config.bg} slide-in`}>
      <Icon className={`w-5 h-5 mt-0.5 ${config.iconColor} flex-shrink-0`} />
      
      <p className={`flex-1 text-sm font-medium ${config.text}`}>
        {message}
      </p>

      <button
        onClick={() => onClose(id)}
        className={`${config.text} hover:opacity-70 transition-opacity flex-shrink-0`}
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

/**
 * Toast Container Component
 */
export const ToastContainer = ({ notifications, onClose }) => {
  if (notifications.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
      {notifications.map((notification) => (
        <Toast
          key={notification.id}
          {...notification}
          onClose={onClose}
        />
      ))}
    </div>
  );
};

export default Toast;