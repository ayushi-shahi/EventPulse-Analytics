import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Activity,
  Bell,
  Key,
  Radio,
  Filter,
  Split,
  X,
} from 'lucide-react';

const NAV = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Live Feed', path: '/live-feed', icon: Radio },
  { name: 'Explorer', path: '/explorer', icon: Filter },
  { name: 'Funnels', path: '/funnels', icon: Split },
  { name: 'Events', path: '/events', icon: Activity },
  { name: 'Alerts', path: '/alerts', icon: Bell },
  { name: 'API Keys', path: '/api-keys', icon: Key },
];

/**
 * Sidebar.
 *
 * Stays `fixed` at every breakpoint. It previously switched to `lg:static` on
 * desktop, which dropped it into normal flow inside Layout's block stack and
 * pushed the main content down by the sidebar's own height — every page then
 * cancelled that with a `-mt-72` negative margin. Keeping it out of flow at
 * all sizes removes the cause instead of the symptom.
 */
const Sidebar = ({ isOpen, onClose }) => (
  <>
    {isOpen && (
      <div
        className="fixed inset-0 bg-black/60 z-40 lg:hidden"
        onClick={onClose}
        aria-hidden
      />
    )}

    <aside
      className={`fixed left-0 z-50 w-64 bg-ink-900 border-r border-ink-700
                  top-0 h-full lg:top-14 lg:h-[calc(100vh-3.5rem)]
                  flex flex-col transform transition-transform duration-200 ease-out
                  lg:translate-x-0 ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
    >
      {/* Mobile-only header; on desktop the Navbar already shows the brand. */}
      <div className="lg:hidden flex items-center justify-between h-14 px-4 border-b border-ink-700">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-brand-600 rounded-lg grid place-items-center">
            <span className="text-white font-bold text-xs">EP</span>
          </div>
          <span className="font-semibold text-gray-100">EventPulse</span>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-lg text-gray-400 hover:bg-ink-800 hover:text-gray-200"
          aria-label="Close menu"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto p-3">
        <div className="space-y-0.5">
          {NAV.map(({ name, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 h-9 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-brand-600/15 text-brand-300 font-medium'
                    : 'text-gray-400 hover:bg-ink-800 hover:text-gray-200'
                }`
              }
            >
              <Icon className="w-[18px] h-[18px] shrink-0" />
              <span>{name}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="p-3 border-t border-ink-700">
        <p className="text-[11px] text-gray-600 text-center">EventPulse Analytics</p>
      </div>
    </aside>
  </>
);

export default Sidebar;
