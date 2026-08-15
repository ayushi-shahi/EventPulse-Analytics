import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

function compact(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(abs >= 10_000 ? 0 : 1)}k`;
  return Number.isInteger(n) ? String(n) : n.toFixed(2);
}

/**
 * A single headline number.
 *
 * The value is the loudest thing in the tile; the label and delta are quiet.
 * Deltas are only rendered when a comparison actually exists — an arrow that
 * always points up teaches the reader to ignore it.
 */
export default function StatTile({
  label,
  value,
  delta = null,
  deltaLabel = 'vs previous period',
  icon: Icon,
  loading = false,
  hint,
}) {
  const dir = delta === null ? null : delta > 0.5 ? 'up' : delta < -0.5 ? 'down' : 'flat';
  const DeltaIcon = dir === 'up' ? ArrowUpRight : dir === 'down' ? ArrowDownRight : Minus;
  const deltaTone =
    dir === 'up' ? 'text-ok' : dir === 'down' ? 'text-bad' : 'text-gray-500';

  return (
    <div className="panel p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
        {Icon && <Icon className="w-4 h-4 text-gray-600 shrink-0" strokeWidth={1.75} />}
      </div>

      {loading ? (
        <div className="skel h-8 w-24 mt-3" />
      ) : (
        <p className="text-metric text-gray-50 mt-2 tnum">{compact(value)}</p>
      )}

      <div className="mt-1.5 min-h-[18px]">
        {!loading && dir && (
          <p className={`flex items-center gap-1 text-xs ${deltaTone}`}>
            <DeltaIcon className="w-3.5 h-3.5" />
            <span className="tnum font-medium">{Math.abs(delta).toFixed(1)}%</span>
            <span className="text-gray-600">{deltaLabel}</span>
          </p>
        )}
        {!loading && !dir && hint && <p className="text-xs text-gray-600">{hint}</p>}
      </div>
    </div>
  );
}
