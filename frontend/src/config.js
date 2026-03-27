// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8002/api/v1',
  WS_URL: import.meta.env.VITE_WS_URL || 'ws://localhost:8002/api/v1',
  TIMEOUT: 60000,
};

// App Configuration
export const APP_CONFIG = {
  APP_NAME: 'EventPulse Analytics',
  VERSION: '1.0.0',
  REFRESH_INTERVAL: 30000, // 30 seconds
  MAX_EVENTS_DISPLAY: 1000,
  DEFAULT_PAGE_SIZE: 100,
  TOAST_DURATION: 5000,
};

// Chart Colors
export const CHART_COLORS = {
  primary: '#3b82f6',
  secondary: '#8b5cf6',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#06b6d4',
  purple: '#a855f7',
  pink: '#ec4899',
};

// Severity Colors
export const SEVERITY_COLORS = {
  info: { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-500' },
  warning: { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-500' },
  error: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-500' },
  critical: { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-500' },
};

// Event Type Colors
export const EVENT_COLORS = [
  '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', 
  '#10b981', '#06b6d4', '#ef4444', '#a855f7'
];

// Period Options
export const PERIOD_OPTIONS = [
  { value: 'last_hour', label: 'Last Hour' },
  { value: 'last_24h', label: 'Last 24 Hours' },
  { value: 'last_7d', label: 'Last 7 Days' },
];

// Metric Options
export const METRIC_OPTIONS = [
  { value: 'events_per_minute', label: 'Events per Minute' },
  { value: 'events_per_hour', label: 'Events per Hour' },
  { value: 'active_users_1m', label: 'Active Users (1 min)' },
  { value: 'active_users_1h', label: 'Active Users (1 hour)' },
];

// Operator Options
export const OPERATOR_OPTIONS = [
  { value: '>', label: 'Greater than (>)' },
  { value: '<', label: 'Less than (<)' },
  { value: '>=', label: 'Greater or equal (>=)' },
  { value: '<=', label: 'Less or equal (<=)' },
  { value: '==', label: 'Equal to (==)' },
  { value: '!=', label: 'Not equal to (!=)' },
];

// Severity Options
export const SEVERITY_OPTIONS = [
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'error', label: 'Error' },
  { value: 'critical', label: 'Critical' },
];

export default {
  API_CONFIG,
  APP_CONFIG,
  CHART_COLORS,
  SEVERITY_COLORS,
  EVENT_COLORS,
};