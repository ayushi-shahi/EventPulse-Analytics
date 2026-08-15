import React from 'react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

export const VIZ = ['#818cf8', '#22d3ee', '#4ade80', '#fbbf24', '#fb7185', '#c084fc', '#38bdf8', '#a3e635'];

const AXIS = { stroke: 'transparent', tick: { fill: '#6b7280', fontSize: 11 }, tickLine: false, axisLine: false };

function fmtNum(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  return String(n);
}

/** One tooltip for every chart, so hover feels the same everywhere. */
function ChartTooltip({ active, payload, label, valueLabel = 'Events' }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-ink-600 bg-ink-850 px-3 py-2 shadow-pop">
      <p className="text-[11px] text-gray-500 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} className="text-sm text-gray-100 tnum">
          <span
            className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle"
            style={{ background: p.color || p.fill }}
          />
          {fmtNum(p.value)}
          <span className="text-gray-500 text-xs ml-1">{valueLabel}</span>
        </p>
      ))}
    </div>
  );
}

/**
 * Time series. Area rather than line: the filled shape makes volume changes
 * legible at a glance, which is what this chart is for.
 */
export function TimeSeries({ data = [], height = 260, valueLabel = 'Events', color = VIZ[0] }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
        <defs>
          <linearGradient id="ts-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" {...AXIS} minTickGap={28} />
        <YAxis {...AXIS} width={48} tickFormatter={fmtNum} allowDecimals={false} />
        <Tooltip content={<ChartTooltip valueLabel={valueLabel} />} cursor={{ stroke: '#2d3242' }} />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          fill="url(#ts-fill)"
          isAnimationActive={false}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/**
 * Ranked categories. Horizontal because category names are words — rotating
 * them under a vertical axis would make them unreadable.
 */
export function RankedBars({ data = [], height = 260, valueLabel = 'Events' }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 4, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" {...AXIS} tickFormatter={fmtNum} />
        <YAxis
          type="category"
          dataKey="label"
          {...AXIS}
          width={116}
          tick={{ fill: '#9ca3af', fontSize: 11 }}
        />
        <Tooltip content={<ChartTooltip valueLabel={valueLabel} />} cursor={{ fill: '#ffffff08' }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive={false} barSize={16}>
          {data.map((_, i) => (
            <Cell key={i} fill={VIZ[i % VIZ.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Share of total as a single stacked strip plus a legend.
 *
 * Preferred over a pie: humans compare lengths far more accurately than
 * angles, and this stays readable with 8+ categories where a pie does not.
 */
export function ShareBar({ items = [], total = 0 }) {
  if (!items.length) return null;
  const sum = total || items.reduce((a, b) => a + b.count, 0) || 1;

  return (
    <div>
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-ink-800">
        {items.map((it, i) => (
          <div
            key={it.label}
            style={{ width: `${(it.count / sum) * 100}%`, background: VIZ[i % VIZ.length] }}
            title={`${it.label}: ${it.count}`}
          />
        ))}
      </div>
      <ul className="mt-4 space-y-2">
        {items.map((it, i) => (
          <li key={it.label} className="flex items-center gap-2.5 text-sm">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: VIZ[i % VIZ.length] }}
            />
            <span className="flex-1 truncate text-gray-300">{it.label}</span>
            <span className="tnum text-gray-500 text-xs">{fmtNum(it.count)}</span>
            <span className="tnum text-gray-200 w-12 text-right">
              {((it.count / sum) * 100).toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export { fmtNum };
