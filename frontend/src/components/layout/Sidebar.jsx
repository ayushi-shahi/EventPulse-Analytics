import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Activity,
  Bell,
  Key,
  BarChart2,
  Radio,
  X,
} from 'lucide-react';

/**
 * Sidebar Navigation Component
 */
const Sidebar = ({ isOpen, onClose }) => {
  const navItems = [
    {
      name: 'Dashboard',
      path: '/dashboard',
      icon: LayoutDashboard,
    },
    {
      name: 'Live Feed',
      path: '/live-feed',
      icon: Radio,
    },
    {
      name: 'Events',
      path: '/events',
      icon: Activity,
    },
    {
      name: 'Metrics',
      path: '/metrics',
      icon: BarChart2,
    },
    {
      name: 'Alerts',
      path: '/alerts',
      icon: Bell,
    },
    {
      name: 'API Keys',
      path: '/api-keys',
      icon: Key,
    },
  ];

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 h-full bg-white border-r border-gray-200 z-50
          w-64 transform transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Mobile Header */}
        <div className="lg:hidden flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">EP</span>
            </div>
            <h2 className="text-lg font-bold text-gray-900">EventPulse</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 mt-16 lg:mt-0">
          <div className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => onClose()}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                      isActive
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`
                  }
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </div>
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="text-xs text-gray-500 text-center">
            <p>EventPulse Analytics v1.0.0</p>
            <p className="mt-1">© 2024 All rights reserved</p>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;