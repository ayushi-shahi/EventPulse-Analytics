import { format, formatDistanceToNow, parseISO } from 'date-fns';

/**
 * Format date to readable string
 */
export const formatDate = (date, formatStr = 'MMM dd, yyyy HH:mm:ss') => {
  if (!date) return 'N/A';
  try {
    const parsedDate = typeof date === 'string' ? parseISO(date) : date;
    return format(parsedDate, formatStr);
  } catch (error) {
    return 'Invalid date';
  }
};

/**
 * Format relative time (e.g., "2 minutes ago")
 */
export const formatRelativeTime = (date) => {
  if (!date) return 'N/A';
  try {
    const parsedDate = typeof date === 'string' ? parseISO(date) : date;
    return formatDistanceToNow(parsedDate, { addSuffix: true });
  } catch (error) {
    return 'Invalid date';
  }
};

/**
 * Format number with commas
 */
export const formatNumber = (num) => {
  if (num === null || num === undefined) return '0';
  return new Intl.NumberFormat('en-US').format(num);
};

/**
 * Format large numbers with K, M, B suffixes
 */
export const formatCompactNumber = (num) => {
  if (num === null || num === undefined) return '0';
  
  const absNum = Math.abs(num);
  
  if (absNum >= 1e9) {
    return (num / 1e9).toFixed(1) + 'B';
  }
  if (absNum >= 1e6) {
    return (num / 1e6).toFixed(1) + 'M';
  }
  if (absNum >= 1e3) {
    return (num / 1e3).toFixed(1) + 'K';
  }
  
  return num.toString();
};

/**
 * Format percentage
 */
export const formatPercentage = (value, decimals = 1) => {
  if (value === null || value === undefined) return '0%';
  return `${value.toFixed(decimals)}%`;
};

/**
 * Format bytes to human readable
 */
export const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Truncate string with ellipsis
 */
export const truncate = (str, maxLength = 50) => {
  if (!str) return '';
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength) + '...';
};

/**
 * Format JSON for display
 */
export const formatJSON = (obj, indent = 2) => {
  if (!obj) return '';
  try {
    return JSON.stringify(obj, null, indent);
  } catch (error) {
    return String(obj);
  }
};

/**
 * Format API key (show only first/last chars)
 */
export const formatAPIKey = (key) => {
  if (!key) return '';
  if (key.length <= 16) return key;
  return `${key.substring(0, 8)}...${key.substring(key.length - 8)}`;
};

/**
 * Format duration in seconds to readable string
 */
export const formatDuration = (seconds) => {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}d`;
};

/**
 * Format rate (events/min, etc)
 */
export const formatRate = (value, unit = '/min', decimals = 2) => {
  if (value === null || value === undefined) return `0${unit}`;
  return `${value.toFixed(decimals)}${unit}`;
};

/**
 * Get initials from email
 */
export const getInitials = (email) => {
  if (!email) return '?';
  const parts = email.split('@')[0].split('.');
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return email.substring(0, 2).toUpperCase();
};

/**
 * Copy text to clipboard
 */
export const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      document.body.removeChild(textArea);
      return true;
    } catch (err) {
      document.body.removeChild(textArea);
      return false;
    }
  }
};

export default {
  formatDate,
  formatRelativeTime,
  formatNumber,
  formatCompactNumber,
  formatPercentage,
  formatBytes,
  truncate,
  formatJSON,
  formatAPIKey,
  formatDuration,
  formatRate,
  getInitials,
  copyToClipboard,
};