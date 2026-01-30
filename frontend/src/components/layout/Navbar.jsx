import React, { useState } from 'react';
import { Menu, X, User, LogOut, Key, Bell, Settings } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useAPIKey } from '../../hooks/useAPIKey';
import { useNavigate } from 'react-router-dom';
import { formatAPIKey, getInitials } from '../../utils/formatters';
import Badge from '../common/Badge';

/**
 * Top Navigation Bar Component
 */
const Navbar = ({ onMenuClick }) => {
  const { user, logout } = useAuth();
  const { selectedAPIKey } = useAPIKey();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-white border-b border-gray-200 fixed top-0 left-0 right-0 z-40 h-16">
      <div className="flex items-center justify-between h-full px-4 lg:px-6">
        {/* Left Section */}
        <div className="flex items-center gap-4">
          {/* Mobile Menu Button */}
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <Menu className="w-6 h-6 text-gray-600" />
          </button>

          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">EP</span>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-xl font-bold text-gray-900">
                EventPulse
              </h1>
              <p className="text-xs text-gray-500">Analytics Platform</p>
            </div>
          </div>
        </div>

        {/* Center Section - Selected API Key */}
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

        {/* Right Section */}
        <div className="flex items-center gap-3">
          {/* Notifications Button */}
          <button className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <Bell className="w-5 h-5 text-gray-600" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-semibold">
                  {getInitials(user?.email)}
                </span>
              </div>
              <span className="hidden sm:block text-sm font-medium text-gray-700">
                {user?.email}
              </span>
            </button>

            {/* Dropdown Menu */}
            {showUserMenu && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setShowUserMenu(false)}
                />
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                  <div className="px-4 py-3 border-b border-gray-200">
                    <p className="text-sm font-medium text-gray-900">{user?.email}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Role: {user?.role || 'User'}
                    </p>
                  </div>

                  <button
                    onClick={() => {
                      navigate('/settings');
                      setShowUserMenu(false);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                    Settings
                  </button>

                  <button
                    onClick={() => {
                      navigate('/api-keys');
                      setShowUserMenu(false);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <Key className="w-4 h-4" />
                    API Keys
                  </button>

                  <hr className="my-1 border-gray-200" />

                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    Logout
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