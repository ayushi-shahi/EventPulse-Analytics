import React from 'react';

/**
 * The single surface primitive. Every card, chart container and table in the
 * app is a Panel, so spacing, borders and header treatment stay identical
 * without each page re-inventing them.
 */
export function Panel({ title, subtitle, actions, children, className = '', bodyClassName = 'p-5' }) {
  return (
    <section className={`panel ${className}`}>
      {(title || actions) && (
        <header className="panel-hd">
          <div className="min-w-0">
            {title && <h2 className="panel-ttl truncate">{title}</h2>}
            {subtitle && <p className="text-xs text-gray-500 mt-0.5 truncate">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </header>
      )}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

/** Uniform loading placeholder so panels never collapse while fetching. */
export function PanelSkeleton({ rows = 4, height = 'h-4' }) {
  return (
    <div className="space-y-2.5" aria-busy="true">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={`skel ${height}`}
          style={{ width: `${92 - i * 11}%` }}
        />
      ))}
    </div>
  );
}

export function PanelEmpty({ icon: Icon, title, hint }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-10 px-4">
      {Icon && <Icon className="w-7 h-7 text-gray-600 mb-3" strokeWidth={1.5} />}
      <p className="text-sm text-gray-400">{title}</p>
      {hint && <p className="text-xs text-gray-600 mt-1 max-w-xs">{hint}</p>}
    </div>
  );
}

export default Panel;
