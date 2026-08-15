import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, Users, Zap, Layers, RefreshCw, KeyRound, AlertTriangle, Globe, Monitor,
} from 'lucide-react';
import { useAPIKey } from '../hooks/useAPIKey';
import { useNotification } from '../hooks/useNotification';
import { useWebSocket } from '../hooks/useWebSocket';
import apiClient from '../services/api';
import Panel, { PanelSkeleton, PanelEmpty } from '../components/common/Panel';
import StatTile from '../components/dashboard/StatTile';
import { TimeSeries, RankedBars, ShareBar } from '../components/dashboard/Charts';

const PERIODS = [
  { value: 'last_hour', label: 'Last hour' },
  { value: 'last_24h', label: 'Last 24 hours' },
  { value: 'last_7d', label: 'Last 7 days' },
];

const REFRESH_MS = 30_000;

// The chart must cover the period the user picked, at a granularity that
// yields a readable number of points. Asking for per-minute data while "Last
// 24 hours" is selected returned only the last hour and rendered a flat line.
const SERIES_FOR = {
  last_hour: { metric: 'events_per_minute', hours: 1, unit: 'minute' },
  last_24h: { metric: 'events_per_hour', hours: 24, unit: 'hour' },
  last_7d: { metric: 'events_per_hour', hours: 24 * 7, unit: 'hour' },
};

function timeLabel(iso, period) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return period === 'last_7d'
    ? d.toLocaleDateString([], { month: 'short', day: 'numeric' })
    : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { selectedAPIKey, hasSelectedKey } = useAPIKey();
  const { error: showError } = useNotification();
  const { rateLimitExceeded } = useWebSocket();

  const [period, setPeriod] = useState('last_24h');
  const [overview, setOverview] = useState(null);
  const [series, setSeries] = useState([]);
  const [breakdowns, setBreakdowns] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [keyInvalid, setKeyInvalid] = useState(false);

  const load = useCallback(async () => {
    if (!hasSelectedKey) return;
    setKeyInvalid(false);

    const cfg = SERIES_FOR[period] ?? SERIES_FOR.last_24h;
    const windowEnd = new Date().toISOString();
    const windowStart = new Date(Date.now() - cfg.hours * 3600_000).toISOString();

    try {
      // One period drives the whole page, so fetch together and surface a
      // failure once rather than five times. Breakdowns are optional extras:
      // if the backend predates them, the core dashboard still renders.
      const [ov, ts, device, country, plan] = await Promise.all([
        apiClient.getOverviewMetrics(period),
        apiClient.getTimeSeries(cfg.metric, windowStart, windowEnd),
        apiClient.getBreakdown('device', period, null, 6).catch(() => null),
        apiClient.getBreakdown('country', period, null, 6).catch(() => null),
        apiClient.getBreakdown('plan', period, null, 6).catch(() => null),
      ]);

      setOverview(ov);
      setSeries(
        (ts?.data_points || []).map((p) => ({
          label: timeLabel(p.timestamp, period),
          value: p.value ?? 0,
        }))
      );
      setBreakdowns({ device, country, plan });
    } catch (err) {
      if (err?.isAPIKeyError) setKeyInvalid(true);
      else showError(err?.message || 'Could not load dashboard');
    } finally {
      setLoading(false);
    }
  }, [period, hasSelectedKey, showError]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  useEffect(() => {
    if (!hasSelectedKey || keyInvalid) return;
    const id = setInterval(load, REFRESH_MS);
    return () => clearInterval(id);
  }, [hasSelectedKey, keyInvalid, load]);

  const refresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  if (!hasSelectedKey) {
    return (
      <div className="max-w-md mx-auto mt-16">
        <Panel>
          <PanelEmpty
            icon={KeyRound}
            title="No data source selected"
            hint="Choose an API key to scope the dashboard, or create one to start collecting events."
          />
          <button className="btn-primary w-full mt-2" onClick={() => navigate('/api-keys')}>
            Go to API Keys
          </button>
        </Panel>
      </div>
    );
  }

  if (keyInvalid) {
    return (
      <div className="max-w-md mx-auto mt-16">
        <Panel>
          <PanelEmpty
            icon={AlertTriangle}
            title="That API key is no longer valid"
            hint="It may have been revoked. Pick a different key or create a new one."
          />
          <div className="flex gap-2 mt-2">
            <button className="btn-primary flex-1" onClick={() => navigate('/api-keys')}>
              API Keys
            </button>
            <button className="btn-ghost flex-1" onClick={refresh}>Retry</button>
          </div>
        </Panel>
      </div>
    );
  }

  const top = (overview?.top_events || []).map((e) => ({
    label: e.event_name,
    value: e.count,
  }));

  return (
    <div className="max-w-[1600px] mx-auto space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-lg font-semibold text-gray-100">Dashboard</h1>
          <p className="text-sm text-gray-500 truncate">{selectedAPIKey?.client_name}</p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-ink-600 overflow-hidden">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`h-9 px-3 text-sm transition-colors ${
                  period === p.value
                    ? 'bg-brand-600/20 text-brand-300 font-medium'
                    : 'text-gray-400 hover:bg-ink-800 hover:text-gray-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button className="btn-ghost" onClick={refresh} disabled={refreshing}>
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </header>

      {rateLimitExceeded && (
        <div className="flex items-start gap-2.5 rounded-lg border border-warn/30 bg-warn/10 px-4 py-3">
          <AlertTriangle className="w-4 h-4 text-warn shrink-0 mt-0.5" />
          <p className="text-sm text-warn/90">
            This API key has hit its rate limit — figures below may be incomplete.
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile label="Events" value={overview?.total_events} icon={Activity}
                  loading={loading} hint={PERIODS.find((p) => p.value === period)?.label} />
        <StatTile label="Events / min" value={overview?.events_per_minute} icon={Zap}
                  loading={loading} hint="average rate" />
        <StatTile label="Active users" value={overview?.active_users} icon={Users}
                  loading={loading} hint="unique in period" />
        <StatTile label="Event types" value={overview?.unique_event_types} icon={Layers}
                  loading={loading} hint="distinct names" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Panel
          className="xl:col-span-2"
          title="Volume over time"
          subtitle={`events per ${(SERIES_FOR[period] ?? SERIES_FOR.last_24h).unit}`}
          bodyClassName="p-4 pt-5"
        >
          {loading ? (
            <PanelSkeleton rows={1} height="h-[260px]" />
          ) : series.length === 0 ? (
            <PanelEmpty icon={Activity} title="No data in this period" />
          ) : (
            <TimeSeries data={series} />
          )}
        </Panel>

        <Panel title="Top events" subtitle="by volume" bodyClassName="p-4 pt-5">
          {loading ? (
            <PanelSkeleton rows={5} />
          ) : top.length === 0 ? (
            <PanelEmpty icon={Layers} title="Nothing recorded yet" />
          ) : (
            <RankedBars data={top} />
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <BreakdownPanel title="Devices" icon={Monitor} data={breakdowns.device}
                        loading={loading} onExplore={() => navigate('/explorer')} />
        <BreakdownPanel title="Countries" icon={Globe} data={breakdowns.country}
                        loading={loading} onExplore={() => navigate('/explorer')} />
        <BreakdownPanel title="Plans" icon={Layers} data={breakdowns.plan}
                        loading={loading} onExplore={() => navigate('/explorer')} />
      </div>
    </div>
  );
}

function BreakdownPanel({ title, icon, data, loading, onExplore }) {
  return (
    <Panel
      title={title}
      subtitle="share of events"
      actions={
        <button onClick={onExplore} className="text-xs text-brand-400 hover:text-brand-300">
          Explore →
        </button>
      }
    >
      {loading ? (
        <PanelSkeleton rows={4} />
      ) : !data?.items?.length ? (
        <PanelEmpty icon={icon} title="No data" />
      ) : (
        <ShareBar items={data.items} total={data.total} />
      )}
    </Panel>
  );
}
