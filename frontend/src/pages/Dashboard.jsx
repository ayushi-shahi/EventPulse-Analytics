import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Users, TrendingUp, BarChart2, RefreshCw } from 'lucide-react';
import { useAPIKey } from '../hooks/useAPIKey';
import { useNotification } from '../hooks/useNotification';
import apiClient from '../services/api';
import MetricCard from '../components/dashboard/MetricCard';
import TimeSeriesChart from '../components/dashboard/TimeSeriesChart';
import TopEventsChart from '../components/dashboard/TopEventsChart';
import Select from '../components/common/Select';
import Button from '../components/common/Button';
import EmptyState from '../components/common/EmptyState';
import { PERIOD_OPTIONS, APP_CONFIG } from '../config';

/**
 * Dashboard Page Component
 */
const Dashboard = () => {
  const { selectedAPIKey, hasSelectedKey } = useAPIKey();
  const { error: showError } = useNotification();

  const [period, setPeriod] = useState('last_hour');
  const [overview, setOverview] = useState(null);
  const [timeSeries, setTimeSeries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Fetch overview metrics
  const fetchOverview = useCallback(async () => {
    if (!hasSelectedKey) return;

    try {
      setLoading(true);
      const data = await apiClient.getOverviewMetrics(period);
      setOverview(data);
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  }, [period, hasSelectedKey, showError]);

  // Fetch time series data
  const fetchTimeSeries = useCallback(async () => {
    if (!hasSelectedKey) return;

    try {
      const data = await apiClient.getTimeSeries('events_per_minute');
      setTimeSeries(data.data_points || []);
    } catch (err) {
      console.error('Failed to fetch time series:', err);
    }
  }, [hasSelectedKey]);

  // Initial fetch
  useEffect(() => {
    if (hasSelectedKey) {
      fetchOverview();
      fetchTimeSeries();
    }
  }, [hasSelectedKey, fetchOverview, fetchTimeSeries]);

  // Auto-refresh
  useEffect(() => {
    if (!hasSelectedKey) return;

    const interval = setInterval(() => {
      fetchOverview();
      fetchTimeSeries();
    }, APP_CONFIG.REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [hasSelectedKey, fetchOverview, fetchTimeSeries]);

  // Manual refresh
  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchOverview(), fetchTimeSeries()]);
    setRefreshing(false);
  };

  // No API key selected
  if (!hasSelectedKey) {
    return (
      <div className="max-w-7xl mx-auto">
        <EmptyState
          icon={BarChart2}
          title="No API Key Selected"
          description="Please select or create an API key to view your dashboard metrics."
          actionLabel="Go to API Keys"
          onAction={() => window.location.href = '/api-keys'}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Real-time analytics for {selectedAPIKey?.client_name}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            options={PERIOD_OPTIONS}
            className="w-40"
          />

          <Button
            variant="outline"
            icon={RefreshCw}
            onClick={handleRefresh}
            loading={refreshing}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Events"
          value={overview?.total_events || 0}
          icon={Activity}
          iconColor="blue"
          subtitle={`in ${PERIOD_OPTIONS.find(p => p.value === period)?.label}`}
          loading={loading}
        />

        <MetricCard
          title="Events per Minute"
          value={overview?.events_per_minute?.toFixed(2) || '0.00'}
          icon={TrendingUp}
          iconColor="green"
          subtitle="average rate"
          loading={loading}
        />

        <MetricCard
          title="Active Users"
          value={overview?.active_users || 0}
          icon={Users}
          iconColor="purple"
          subtitle="unique users"
          loading={loading}
        />

        <MetricCard
          title="Event Types"
          value={overview?.unique_event_types || 0}
          icon={BarChart2}
          iconColor="pink"
          subtitle="unique types"
          loading={loading}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TimeSeriesChart
          title="Events per Minute"
          data={timeSeries}
          loading={loading}
          height={350}
        />

        <TopEventsChart
          title="Top Events"
          data={overview?.top_events || []}
          loading={loading}
          height={350}
        />
      </div>
    </div>
  );
};

export default Dashboard;