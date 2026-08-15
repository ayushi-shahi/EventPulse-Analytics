import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Split, KeyRound, RefreshCw, X, Plus } from 'lucide-react';
import { useAPIKey } from '../hooks/useAPIKey';
import { useNotification } from '../hooks/useNotification';
import apiClient from '../services/api';
import Panel, { PanelSkeleton, PanelEmpty } from '../components/common/Panel';
import { VIZ, fmtNum } from '../components/dashboard/Charts';

const PERIODS = [
  { value: 'last_24h', label: 'Last 24 hours' },
  { value: 'last_7d', label: 'Last 7 days' },
  { value: 'last_30d', label: 'Last 30 days' },
];

const PRESETS = [
  {
    name: 'Signup to purchase',
    steps: ['signup_started', 'signup_completed', 'checkout_started', 'purchase_completed'],
  },
  { name: 'Visit to signup', steps: ['page_view', 'signup_started', 'signup_completed'] },
  { name: 'Activation', steps: ['signup_completed', 'login', 'feature_used'] },
];

/**
 * Funnels — where users drop out of a multi-step flow.
 *
 * Bars are scaled against the first step so the drop-off is visible as
 * shrinking width. Showing each step at full width with only a percentage
 * label would hide the very thing the chart exists to communicate.
 */
export default function Funnels() {
  const navigate = useNavigate();
  const { selectedAPIKey, hasSelectedKey } = useAPIKey();
  const { error: showError } = useNotification();

  const [steps, setSteps] = useState(PRESETS[0].steps);
  const [period, setPeriod] = useState('last_30d');
  const [available, setAvailable] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hasSelectedKey) return;
    apiClient
      .getTopEvents('last_7d', 20)
      .then((r) => setAvailable((r?.top_events || []).map((e) => e.event_name)))
      .catch(() => setAvailable([]));
  }, [hasSelectedKey]);

  const load = useCallback(async () => {
    if (!hasSelectedKey || steps.length < 2) return;
    setLoading(true);
    try {
      setResult(await apiClient.getFunnel(steps, period));
    } catch (err) {
      showError(err?.message || 'Could not compute funnel');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [steps, period, hasSelectedKey, showError]);

  useEffect(() => { load(); }, [load]);

  if (!hasSelectedKey) {
    return (
      <div className="max-w-md mx-auto mt-16">
        <Panel>
          <PanelEmpty icon={KeyRound} title="No data source selected"
                      hint="Pick an API key to build a funnel from its events." />
          <button className="btn-primary w-full mt-2" onClick={() => navigate('/api-keys')}>
            Go to API Keys
          </button>
        </Panel>
      </div>
    );
  }

  const rows = result?.steps || [];
  const first = rows[0]?.users || 0;

  return (
    <div className="max-w-[1400px] mx-auto space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-100">Funnels</h1>
          <p className="text-sm text-gray-500">
            Conversion across steps · {selectedAPIKey?.client_name}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select className="field w-40" value={period} onChange={(e) => setPeriod(e.target.value)}>
            {PERIODS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
          <button className="btn-ghost" onClick={load}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      <Panel title="Steps" subtitle="in order — a user counts only if they reached every earlier step"
             bodyClassName="p-4">
        <div className="flex flex-wrap gap-2 mb-4">
          {PRESETS.map((p) => (
            <button
              key={p.name}
              onClick={() => setSteps(p.steps)}
              className={`chip ${
                steps.join() === p.steps.join()
                  ? 'border-brand-500/40 bg-brand-600/15 text-brand-300'
                  : 'border-ink-600 text-gray-400 hover:bg-ink-800'
              }`}
            >
              {p.name}
            </button>
          ))}
        </div>

        <div className="space-y-2">
          {steps.map((s, i) => (
            <div key={`${s}-${i}`} className="flex items-center gap-2">
              <span className="w-5 text-xs text-gray-600 tnum">{i + 1}</span>
              <select
                className="field flex-1"
                value={s}
                onChange={(e) => setSteps(steps.map((v, idx) => (idx === i ? e.target.value : v)))}
              >
                {[...new Set([s, ...available])].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              <button
                onClick={() => setSteps(steps.filter((_, idx) => idx !== i))}
                disabled={steps.length <= 2}
                className="btn-ghost h-9 w-9 !px-0 disabled:opacity-30"
                aria-label={`Remove step ${i + 1}`}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>

        {steps.length < 8 && available.length > 0 && (
          <button
            className="btn-ghost mt-3"
            onClick={() => setSteps([...steps, available.find((a) => !steps.includes(a)) || available[0]])}
          >
            <Plus className="w-4 h-4" /> Add step
          </button>
        )}
      </Panel>

      <Panel
        title="Conversion"
        subtitle={result ? `${result.overall_conversion}% complete the full journey` : ' '}
        bodyClassName="p-5"
      >
        {loading ? (
          <PanelSkeleton rows={4} height="h-12" />
        ) : rows.length === 0 ? (
          <PanelEmpty icon={Split} title="No data for these steps"
                      hint="Try a longer period or different event names." />
        ) : (
          <div className="space-y-3">
            {rows.map((r, i) => {
              const width = first ? Math.max((r.users / first) * 100, 1.5) : 0;
              return (
                <div key={`${r.step}-${i}`}>
                  <div className="flex items-baseline justify-between gap-3 mb-1.5">
                    <span className="text-sm text-gray-300 truncate">
                      <span className="text-gray-600 tnum mr-2">{i + 1}</span>
                      {r.step}
                    </span>
                    <span className="text-sm text-gray-100 tnum shrink-0">
                      {fmtNum(r.users)}
                      <span className="text-gray-500 text-xs ml-1.5">users</span>
                    </span>
                  </div>

                  <div className="h-8 w-full rounded-lg bg-ink-850 overflow-hidden">
                    <div
                      className="h-full rounded-lg transition-all duration-500 flex items-center px-3"
                      style={{ width: `${width}%`, background: VIZ[i % VIZ.length] + '33',
                               borderLeft: `3px solid ${VIZ[i % VIZ.length]}` }}
                    >
                      <span className="text-xs font-medium tnum" style={{ color: VIZ[i % VIZ.length] }}>
                        {r.conversion_from_start}%
                      </span>
                    </div>
                  </div>

                  {i > 0 && (
                    <p className="text-xs text-gray-600 mt-1">
                      {r.conversion_from_previous}% continued from the previous step
                      {r.dropped > 0 && (
                        <span className="text-bad/80"> · {fmtNum(r.dropped)} dropped off</span>
                      )}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}
