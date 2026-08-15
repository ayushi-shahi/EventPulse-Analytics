import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { formatNumber, formatPercentage } from '../../utils/formatters';
import { EVENT_COLORS } from '../../config';
import Card from '../common/Card';
import Spinner from '../common/Spinner';

/**
 * Top Events Bar Chart Component
 */
const TopEventsChart = ({
  title = 'Top Events',
  data = [],
  loading = false,
  height = 300,
}) => {
  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-ink-900 border border-ink-700 rounded-lg shadow-lg p-3">
          <p className="text-sm font-semibold text-gray-100">{data.event_name}</p>
          <p className="text-sm text-gray-400 mt-1">
            Count: <span className="font-semibold">{formatNumber(data.count)}</span>
          </p>
          {data.percentage !== undefined && (
            <p className="text-sm text-gray-400">
              Percentage: <span className="font-semibold">{formatPercentage(data.percentage)}</span>
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <Card title={title}>
      {loading ? (
        <div className="flex items-center justify-center" style={{ height }}>
          <Spinner message="Loading chart..." />
        </div>
      ) : data.length === 0 ? (
        <div className="flex items-center justify-center text-gray-500" style={{ height }}>
          No events to display
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="event_name"
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickFormatter={formatNumber}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar dataKey="count" name="Event Count" radius={[8, 8, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={EVENT_COLORS[index % EVENT_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
};

export default TopEventsChart;