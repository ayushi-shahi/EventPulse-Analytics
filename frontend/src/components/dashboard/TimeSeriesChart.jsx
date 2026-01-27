import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { formatDate, formatNumber } from '../../utils/formatters';
import Card from '../common/Card';
import Spinner from '../common/Spinner';

/**
 * Time Series Chart Component
 */
const TimeSeriesChart = ({
  title = 'Time Series',
  data = [],
  loading = false,
  dataKey = 'value',
  xAxisKey = 'timestamp',
  color = '#3b82f6',
  height = 300,
}) => {
  // Format data for chart
  const formattedData = data.map((item) => ({
    ...item,
    formattedTime: formatDate(item[xAxisKey], 'HH:mm'),
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <p className="text-sm font-medium text-gray-900">
            {formatDate(data[xAxisKey], 'MMM dd, HH:mm:ss')}
          </p>
          <p className="text-sm text-gray-600 mt-1">
            Value: <span className="font-semibold">{formatNumber(data[dataKey])}</span>
          </p>
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
          No data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={formattedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="formattedTime"
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickFormatter={formatNumber}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
              name="Value"
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
};

export default TimeSeriesChart;