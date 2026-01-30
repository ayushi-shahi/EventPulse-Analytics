import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Users, TrendingUp, BarChart2, RefreshCw, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAPIKey } from '../hooks/useAPIKey';
import { useNotification } from '../hooks/useNotification';
import { useWebSocket } from '../hooks/useWebSocket';
import apiClient from '../services/api';
import MetricCard from '../components/dashboard/MetricCard';
import TimeSeriesChart from '../components/dashboard/TimeSeriesChart';
import TopEventsChart from '../components/dashboard/TopEventsChart';
import Select from '../components/common/Select';
import Button from '../components/common/Button';
import EmptyState from '../components/common/EmptyState';
import Spinner from '../components/common/Spinner';
import { PERIOD_OPTIONS, APP_CONFIG } from '../config';

const Dashboard = () => {
  const navigate = useNavigate();
  const { selectedAPIKey, hasSelectedKey } = useAPIKey();
  const { error: showError, warning } = useNotification();
  const { rateLimitExceeded } = useWebSocket();

  const [period, setPeriod] = useState('last_hour');
  const [overview, setOverview] = useState(null);
  const [timeSeries, setTimeSeries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [apiKeyError, setApiKeyError] = useState(false);

  const fetchOverview = useCallback(async () => {
    if (!hasSelectedKey) return;

    try {
      setLoading(true);
      setApiKeyError(false);
      const data = await apiClient.getOverviewMetrics(period);
      setOverview(data);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      
      if (err.isAPIKeyError) {
        setApiKeyError(true);
        warning('Invalid API key. Please select a valid API key.');
      } else {
        showError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, [period, hasSelectedKey, showError, warning]);

  const fetchTimeSeries = useCallback(async () => {
    if (!hasSelectedKey) return;

    try {
      const data = await apiClient.getTimeSeries('events_per_minute');
      setTimeSeries(data.data_points || []);
    } catch (err) {
      console.error('Failed to fetch time series:', err);
    }
  }, [hasSelectedKey]);

  useEffect(() => {
    if (hasSelectedKey) {
      fetchOverview();
      fetchTimeSeries();
    }
  }, [hasSelectedKey, fetchOverview, fetchTimeSeries]);

  useEffect(() => {
    if (!hasSelectedKey || apiKeyError) return;

    const interval = setInterval(() => {
      fetchOverview();
      fetchTimeSeries();
    }, APP_CONFIG.REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [hasSelectedKey, apiKeyError, fetchOverview, fetchTimeSeries]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchOverview(), fetchTimeSeries()]);
    setRefreshing(false);
  };

  if (!hasSelectedKey) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-8">
        <EmptyState
          icon={BarChart2}
          title="No API Key Selected"
          description="Please select or create an API key to view your dashboard metrics."
          actionLabel="Go to API Keys"
          onAction={() => navigate('/api-keys')}
        />
      </div>
    );
  }

  if (apiKeyError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-8">
        <div className="max-w-2xl w-full bg-red-50 border-2 border-red-200 rounded-2xl p-8 shadow-lg">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-12 h-12 bg-red-500 rounded-xl flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-bold text-red-900 mb-2">
                Invalid API Key
              </h3>
              <p className="text-sm text-red-700 mb-6 leading-relaxed">
                The selected API key is invalid or has been revoked. Please select a different API key or create a new one.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  variant="danger"
                  onClick={() => navigate('/api-keys')}
                >
                  Go to API Keys
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setApiKeyError(false);
                    fetchOverview();
                  }}
                >
                  Try Again
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="space-y-6">
          {/* Rate Limit Warning */}
          {rateLimitExceeded && (
            <div className="bg-amber-50 border-2 border-amber-200 rounded-xl p-4 sm:p-5 shadow-sm">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 sm:w-6 sm:h-6 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm sm:text-base font-semibold text-amber-900">Rate Limit Active</h4>
                  <p className="text-xs sm:text-sm text-amber-700 mt-1">
                    Your API key has reached its rate limit. Some data may be incomplete.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Header */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 sm:p-6 -mt-72">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-blue-500 rounded-xl flex items-center justify-center shadow-lg flex-shrink-0">
                  <BarChart2 className="w-6 h-6 sm:w-7 sm:h-7 text-white" />
                </div>
                <div className="min-w-0 flex-1">
                  <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Dashboard</h1>
                  <p className="text-sm sm:text-base text-gray-600 mt-0.5 truncate">
                    Analytics for <span className="font-semibold text-blue-600">{selectedAPIKey?.client_name}</span>
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                <Select
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                  options={PERIOD_OPTIONS}
                  className="w-full sm:w-44"
                />
                <Button
                  variant="outline"
                  icon={RefreshCw}
                  onClick={handleRefresh}
                  loading={refreshing}
                  className="flex-1 sm:flex-none"
                >
                  Refresh
                </Button>
              </div>
            </div>
          </div>

          {/* Loading State */}
          {loading && !overview ? (
            <div className="flex items-center justify-center py-16 sm:py-20">
              <Spinner size="xl" message="Loading dashboard..." />
            </div>
          ) : (
            <>
              {/* Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
                <MetricCard
                  title="Total Events"
                  value={overview?.total_events || 0}
                  icon={Activity}
                  iconColor="blue"
                  subtitle={`in ${PERIOD_OPTIONS.find((p) => p.value === period)?.label}`}
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
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow">
                  <TimeSeriesChart
                    title="Events per Minute"
                    data={timeSeries}
                    loading={loading}
                    height={350}
                  />
                </div>
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow">
                  <TopEventsChart
                    title="Top Events"
                    data={overview?.top_events || []}
                    loading={loading}
                    height={350}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;