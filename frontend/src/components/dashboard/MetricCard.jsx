import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { formatNumber, formatCompactNumber } from '../../utils/formatters';

/**
 * Metric Card Component for Dashboard
 */
const MetricCard = ({
  title,
  value,
  change = null,
  changeType = 'neutral', // 'positive' | 'negative' | 'neutral'
  icon: Icon,
  iconColor = 'blue',
  subtitle = null,
  loading = false,
}) => {
  const iconColors = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    red: 'bg-red-100 text-red-600',
    purple: 'bg-purple-100 text-purple-600',
    pink: 'bg-pink-100 text-pink-600',
  };

  const getTrendIcon = () => {
    if (changeType === 'positive') return <TrendingUp className="w-4 h-4" />;
    if (changeType === 'negative') return <TrendingDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (changeType === 'positive') return 'text-green-600';
    if (changeType === 'negative') return 'text-red-600';
    return 'text-gray-600';
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse">
        <div className="flex items-center justify-between mb-4">
          <div className="h-4 bg-gray-200 rounded w-24"></div>
          <div className="w-12 h-12 bg-gray-200 rounded-lg"></div>
        </div>
        <div className="h-8 bg-gray-200 rounded w-32 mb-2"></div>
        <div className="h-3 bg-gray-200 rounded w-20"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        {Icon && (
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${iconColors[iconColor]}`}>
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>

      <div className="space-y-2">
        <p className="text-3xl font-bold text-gray-900">
          {typeof value === 'number' ? formatCompactNumber(value) : value}
        </p>

        {(change !== null || subtitle) && (
          <div className="flex items-center gap-2">
            {change !== null && (
              <div className={`flex items-center gap-1 text-sm font-medium ${getTrendColor()}`}>
                {getTrendIcon()}
                <span>{change}</span>
              </div>
            )}
            {subtitle && (
              <p className="text-sm text-gray-500">{subtitle}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MetricCard;