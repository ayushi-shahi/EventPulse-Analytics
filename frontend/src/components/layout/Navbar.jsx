import React, { useState, useEffect } from 'react';
import { Menu, X, User, LogOut, Key, Bell, Settings } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useAPIKey } from '../../hooks/useAPIKey';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useBell } from '../../context/BellContext';
import { useNavigate } from 'react-router-dom';
import { formatAPIKey, getInitials } from '../../utils/formatters';
import Badge from '../common/Badge';

const Navbar = ({ onMenuClick }) => {
  const { user, logout } = useAuth();
  const { selectedAPIKey } = useAPIKey();
  const { lastMessage } = useWebSocket();
  const { items, addBell, clearBell } = useBell();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Listen for alert events from WebSocket
  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type === 'alert_triggered') {
      addBell(
        lastMessage.data?.alert_name
          ? `Alert: ${lastMessage.data.alert_name} triggered`
          : 'An alert was triggered',
        'warning'
      );
      setUnreadCount((c) => c + 1);
    }
  }, [lastMessage]);

  const handleBellOpen = () => {
    setShowNotifications(!showNotifications);
    if (!showNotifications) setUnreadCount(0);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const typeColor = { info: '#3b82f6', warning: '#f59e0b', error: '#ef4444', success: '#10b981' };

  return (
    <nav className="bg-white border-b border-gray-200 fixed top-0 left-0 right-0 z-40 h-16">
      <div className="flex items-center justify-between h-full px-4 lg:px-6">
        {/* Left */}
        <div className="flex items-center gap-4">
          <button onClick={onMenuClick} className="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <Menu className="w-6 h-6 text-gray-600" />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">EP</span>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-xl font-bold text-gray-900">EventPulse</h1>
              <p className="text-xs text-gray-500">Analytics Platform</p>
            </div>
          </div>
        </div>

        {/* Center */}
        <div className="hidden md:flex items-center gap-2">
          {selectedAPIKey ? (
            <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg">
              <Key className="w-4 h-4 text-blue-600" />
              <div className="text-sm">
                <p className="font-medium text-blue-900">{selectedAPIKey.client_name}</p>
                <p className="text-xs text-blue-600 font-mono">
                  {formatAPIKey(selectedAPIKey.api_key || selectedAPIKey.key)}
                </p>
              </div>
            </div>
          ) : (
            <Badge variant="warning">No API Key Selected</Badge>
          )}
        </div>

        {/* Right */}
        <div className="flex items-center gap-3">
          {/* Bell */}
          <div className="relative">
            <button onClick={handleBellOpen} className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors">
              <Bell className="w-5 h-5 text-gray-600" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 rounded-full text-white text-xs flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </button>

            {showNotifications && (
              <>
                <div className="fixed inset-0 z-99" onClick={() => setShowNotifications(false)} />
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-[100]">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                    <p className="text-sm font-semibold text-gray-900">Notifications</p>
                    {items.length > 0 && (
                      <button onClick={clearBell} className="text-xs text-gray-400 hover:text-gray-600">
                        Clear all
                      </button>
                    )}
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {items.length === 0 ? (
                      <p className="text-sm text-gray-500 text-center py-6">No notifications yet</p>
                    ) : (
                      items.map((item) => (
                        <div key={item.id} className="px-4 py-3 border-b border-gray-100 hover:bg-gray-50">
                          <div className="flex items-start gap-2">
                            <span style={{ color: typeColor[item.type], fontSize: 18 }}>●</span>
                            <div>
                              <p className="text-sm text-gray-800">{item.message}</p>
                              <p className="text-xs text-gray-400 mt-0.5">
                                {item.timestamp.toLocaleTimeString()}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* User Menu */}
          <div className="relative">
            <button onClick={() => setShowUserMenu(!showUserMenu)} className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 transition-colors">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-semibold">{getInitials(user?.email)}</span>
              </div>
              <span className="hidden sm:block text-sm font-medium text-gray-700">{user?.email}</span>
            </button>

            {showUserMenu && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowUserMenu(false)} />
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                  <div className="px-4 py-3 border-b border-gray-200">
                    <p className="text-sm font-medium text-gray-900">{user?.email}</p>
                    <p className="text-xs text-gray-500 mt-0.5">Role: {user?.role || 'User'}</p>
                  </div>
                  <button onClick={() => { navigate('/settings'); setShowUserMenu(false); }} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
                    <Settings className="w-4 h-4" />Settings
                  </button>
                  <button onClick={() => { navigate('/api-keys'); setShowUserMenu(false); }} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
                    <Key className="w-4 h-4" />API Keys
                  </button>
                  <hr className="my-1 border-gray-200" />
                  <button onClick={handleLogout} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors">
                    <LogOut className="w-4 h-4" />Logout
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;