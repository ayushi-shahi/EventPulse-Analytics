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
    blue: 'bg-brand-600/20 text-brand-400',
    green: 'bg-ok/20 text-ok',
    yellow: 'bg-warn/20 text-warn',
    red: 'bg-bad/20 text-bad',
    purple: 'bg-viz-6/20 text-viz-6',
    pink: 'bg-viz-5/20 text-viz-5',
  };

  const getTrendIcon = () => {
    if (changeType === 'positive') return <TrendingUp className="w-4 h-4" />;
    if (changeType === 'negative') return <TrendingDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (changeType === 'positive') return 'text-ok';
    if (changeType === 'negative') return 'text-bad';
    return 'text-gray-400';
  };

  if (loading) {
    return (
      <div className="bg-ink-900 rounded-lg shadow-sm border border-ink-700 p-6 animate-pulse">
        <div className="flex items-center justify-between mb-4">
          <div className="h-4 bg-ink-700 rounded w-24"></div>
          <div className="w-12 h-12 bg-ink-700 rounded-lg"></div>
        </div>
        <div className="h-8 bg-ink-700 rounded w-32 mb-2"></div>
        <div className="h-3 bg-ink-700 rounded w-20"></div>
      </div>
    );
  }

  return (
    <div className="bg-ink-900 rounded-lg shadow-sm border border-ink-700 p-6 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-400">{title}</h3>
        {Icon && (
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${iconColors[iconColor]}`}>
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>

      <div className="space-y-2">
        <p className="text-3xl font-bold text-gray-100">
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