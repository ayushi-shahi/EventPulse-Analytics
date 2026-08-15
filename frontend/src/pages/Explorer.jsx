import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Filter, KeyRound, RefreshCw } from 'lucide-react';
import { useAPIKey } from '../hooks/useAPIKey';
import { useNotification } from '../hooks/useNotification';
import apiClient from '../services/api';
import Panel, { PanelSkeleton, PanelEmpty } from '../components/common/Panel';
import { RankedBars, ShareBar, fmtNum } from '../components/dashboard/Charts';

const PERIODS = [
  { value: 'last_hour', label: 'Last hour' },
  { value: 'last_24h', label: 'Last 24 hours' },
  { value: 'last_7d', label: 'Last 7 days' },
  { value: 'last_30d', label: 'Last 30 days' },
];

// Shown first because they answer the most common questions. The full list
// still comes from the backend so the two can never drift apart.
const PRIMARY = ['device', 'browser', 'os', 'country', 'plan', 'path', 'referrer', 'utm_source'];

/**
 * Explorer — slice events by any recorded property.
 *
 * This is where the rich event properties finally become usable: pick a
 * dimension, optionally narrow to one event type, and see the distribution.
 */
export default function Explorer() {
  const navigate = useNavigate();
  const { selectedAPIKey, hasSelectedKey } = useAPIKey();
  const { error: showError } = useNotification();

  const [properties, setProperties] = useState(PRIMARY);
  const [property, setProperty] = useState('device');
  const [period, setPeriod] = useState('last_7d');
  const [eventName, setEventName] = useState('');
  const [eventNames, setEventNames] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Available properties + event names for the filters.
  useEffect(() => {
    if (!hasSelectedKey) return;
    apiClient
      .getBreakdownProperties()
      .then((r) => {
        const all = r?.properties || [];
        // Keep the useful ones up front, then everything else alphabetically.
        setProperties([...PRIMARY.filter((p) => all.includes(p)),
                       ...all.filter((p) => !PRIMARY.includes(p))]);
      })
      .catch(() => {/* falls back to PRIMARY */});

    apiClient
      .getTopEvents(period === 'last_30d' ? 'last_7d' : period, 20)
      .then((r) => setEventNames((r?.top_events || []).map((e) => e.event_name)))
      .catch(() => setEventNames([]));
  }, [hasSelectedKey, period]);

  const load = useCallback(async () => {
    if (!hasSelectedKey) return;
    setLoading(true);
    try {
      setData(await apiClient.getBreakdown(property, period, eventName || null, 15));
    } catch (err) {
      showError(err?.message || 'Could not load breakdown');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [property, period, eventName, hasSelectedKey, showError]);

  useEffect(() => { load(); }, [load]);

  if (!hasSelectedKey) {
    return (
      <div className="max-w-md mx-auto mt-16">
        <Panel>
          <PanelEmpty icon={KeyRound} title="No data source selected"
                      hint="Pick an API key to explore its events." />
          <button className="btn-primary w-full mt-2" onClick={() => navigate('/api-keys')}>
            Go to API Keys
          </button>
        </Panel>
      </div>
    );
  }

  const items = data?.items || [];
  const bars = items.map((i) => ({ label: i.label, value: i.count }));

  return (
    <div className="max-w-[1600px] mx-auto space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-100">Explorer</h1>
          <p className="text-sm text-gray-500">
            Break events down by any property · {selectedAPIKey?.client_name}
          </p>
        </div>
        <button className="btn-ghost" onClick={load}>
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </header>

      <Panel bodyClassName="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <label className="block">
            <span className="text-xs text-gray-500 mb-1.5 block">Break down by</span>
            <select className="field" value={property} onChange={(e) => setProperty(e.target.value)}>
              {properties.map((p) => (
                <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-xs text-gray-500 mb-1.5 block">Event type</span>
            <select className="field" value={eventName} onChange={(e) => setEventName(e.target.value)}>
              <option value="">All events</option>
              {eventNames.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>

          <label className="block">
            <span className="text-xs text-gray-500 mb-1.5 block">Period</span>
            <select className="field" value={period} onChange={(e) => setPeriod(e.target.value)}>
              {PERIODS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </label>
        </div>
      </Panel>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Panel
          className="xl:col-span-2"
          title={`Events by ${property.replace(/_/g, ' ')}`}
          subtitle={eventName ? `restricted to ${eventName}` : 'all event types'}
          bodyClassName="p-4 pt-5"
        >
          {loading ? (
            <PanelSkeleton rows={1} height="h-[320px]" />
          ) : bars.length === 0 ? (
            <PanelEmpty icon={Filter} title="Nothing matches these filters"
                        hint="Try a wider period, or a property this event type actually records." />
          ) : (
            <RankedBars data={bars} height={Math.max(240, bars.length * 26)} />
          )}
        </Panel>

        <Panel title="Share" subtitle={`${fmtNum(data?.total || 0)} events`}>
          {loading ? <PanelSkeleton rows={6} />
            : items.length === 0 ? <PanelEmpty icon={Filter} title="No data" />
            : <ShareBar items={items.slice(0, 8)} total={data?.total} />}
        </Panel>
      </div>

      <Panel title="Detail" subtitle="counts and unique users per value" bodyClassName="p-0">
        {loading ? (
          <div className="p-5"><PanelSkeleton rows={6} /></div>
        ) : items.length === 0 ? (
          <PanelEmpty icon={Filter} title="No rows" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-ink-700">
                  <th className="font-medium px-5 py-2.5">{property.replace(/_/g, ' ')}</th>
                  <th className="font-medium px-5 py-2.5 text-right">Events</th>
                  <th className="font-medium px-5 py-2.5 text-right">Users</th>
                  <th className="font-medium px-5 py-2.5 text-right w-32">Share</th>
                </tr>
              </thead>
              <tbody>
                {items.map((i) => (
                  <tr key={i.label} className="border-b border-ink-800 last:border-0 hover:bg-ink-850/60">
                    <td className="px-5 py-2.5 text-gray-200">{i.label}</td>
                    <td className="px-5 py-2.5 text-right text-gray-300">{fmtNum(i.count)}</td>
                    <td className="px-5 py-2.5 text-right text-gray-400">{fmtNum(i.users)}</td>
                    <td className="px-5 py-2.5">
                      <div className="flex items-center gap-2 justify-end">
                        <div className="w-16 h-1.5 rounded-full bg-ink-800 overflow-hidden">
                          <div className="h-full bg-brand-500" style={{ width: `${i.percentage}%` }} />
                        </div>
                        <span className="text-gray-400 w-12 text-right">{i.percentage}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
