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
      bg: 'bg-ok/10 border-ok',
      text: 'text-ok',
      icon: CheckCircle,
      iconColor: 'text-ok',
    },
    error: {
      bg: 'bg-bad/10 border-bad',
      text: 'text-bad',
      icon: XCircle,
      iconColor: 'text-bad',
    },
    warning: {
      bg: 'bg-warn/10 border-warn',
      text: 'text-warn',
      icon: AlertTriangle,
      iconColor: 'text-warn',
    },
    info: {
      bg: 'bg-brand-600/15 border-brand-500',
      text: 'text-brand-300',
      icon: Info,
      iconColor: 'text-brand-400',
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