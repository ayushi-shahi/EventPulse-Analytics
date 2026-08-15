import React, { useState, useEffect, useRef } from 'react';
import { Menu, LogOut, Key, Bell, Settings, ChevronDown, Check, Wifi, WifiOff } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useAPIKey } from '../../hooks/useAPIKey';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useBell } from '../../context/BellContext';
import { getInitials } from '../../utils/formatters';

function useOutsideClose(ref, onClose, active) {
  useEffect(() => {
    if (!active) return;
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [ref, onClose, active]);
}

const Navbar = ({ onMenuClick }) => {
  const { user, logout } = useAuth();
  const { apiKeys = [], selectedAPIKey, selectAPIKey } = useAPIKey();
  const { lastMessage, isConnected } = useWebSocket();
  const { items, addBell, clearBell } = useBell();
  const navigate = useNavigate();

  const [menu, setMenu] = useState(null); // 'user' | 'bell' | 'keys' | null
  const [unread, setUnread] = useState(0);

  const userRef = useRef(null);
  const bellRef = useRef(null);
  const keyRef = useRef(null);
  useOutsideClose(userRef, () => setMenu(null), menu === 'user');
  useOutsideClose(bellRef, () => setMenu(null), menu === 'bell');
  useOutsideClose(keyRef, () => setMenu(null), menu === 'keys');

  useEffect(() => {
    if (lastMessage?.type === 'alert_triggered') {
      addBell(
        lastMessage.data?.alert_name
          ? `Alert: ${lastMessage.data.alert_name} triggered`
          : 'An alert was triggered',
        'warning'
      );
      setUnread((c) => c + 1);
    }
  }, [lastMessage, addBell]);

  const toggle = (name) => {
    setMenu((m) => (m === name ? null : name));
    if (name === 'bell') setUnread(0);
  };

  const dotColor = { info: 'bg-brand-400', warning: 'bg-warn', error: 'bg-bad', success: 'bg-ok' };

  return (
    <nav className="fixed top-0 inset-x-0 z-40 h-14 bg-ink-900/95 backdrop-blur border-b border-ink-700">
      <div className="flex items-center gap-3 h-full px-4 lg:px-6">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 -ml-2 rounded-lg text-gray-400 hover:bg-ink-800 hover:text-gray-200"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5 lg:w-56">
          <div className="w-7 h-7 bg-brand-600 rounded-lg grid place-items-center shrink-0">
            <span className="text-white font-bold text-xs">EP</span>
          </div>
          <span className="font-semibold text-gray-100 hidden sm:block">EventPulse</span>
        </div>

        {/* Source switcher — which API key the whole dashboard is scoped to. */}
        <div ref={keyRef} className="relative">
          <button
            onClick={() => toggle('keys')}
            className="btn-ghost h-8 max-w-[240px]"
            aria-expanded={menu === 'keys'}
          >
            <Key className="w-3.5 h-3.5 text-gray-500 shrink-0" />
            <span className="truncate">
              {selectedAPIKey?.client_name || 'Select a source'}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-gray-500 shrink-0" />
          </button>

          {menu === 'keys' && (
            <div className="absolute left-0 mt-2 w-64 panel shadow-pop py-1 animate-slide-up">
              <p className="px-3 py-2 text-[11px] uppercase tracking-wide text-gray-500">
                Data source
              </p>
              {apiKeys.length === 0 ? (
                <button
                  onClick={() => { navigate('/api-keys'); setMenu(null); }}
                  className="w-full text-left px-3 py-2 text-sm text-brand-300 hover:bg-ink-800"
                >
                  Create your first API key →
                </button>
              ) : (
                apiKeys.map((k) => (
                  <button
                    key={k.id}
                    onClick={() => { selectAPIKey?.(k); setMenu(null); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-ink-800"
                  >
                    <span className="flex-1 text-left truncate">{k.client_name}</span>
                    {selectedAPIKey?.id === k.id && (
                      <Check className="w-3.5 h-3.5 text-brand-400 shrink-0" />
                    )}
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        <div className="flex-1" />

        {/* Live connection state — this is a real-time product; say so. */}
        <span
          className={`chip hidden sm:inline-flex ${
            isConnected
              ? 'border-ok/30 bg-ok/10 text-ok'
              : 'border-ink-600 bg-ink-800 text-gray-500'
          }`}
          title={isConnected ? 'Streaming live events' : 'Not connected'}
        >
          {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
          {isConnected ? 'Live' : 'Offline'}
        </span>

        <div ref={bellRef} className="relative">
          <button
            onClick={() => toggle('bell')}
            className="relative p-2 rounded-lg text-gray-400 hover:bg-ink-800 hover:text-gray-200"
            aria-label="Notifications"
          >
            <Bell className="w-[18px] h-[18px]" />
            {unread > 0 && (
              <span className="absolute top-1 right-1 min-w-[15px] h-[15px] px-1 bg-bad rounded-full text-white text-[10px] font-semibold grid place-items-center">
                {unread > 9 ? '9+' : unread}
              </span>
            )}
          </button>

          {menu === 'bell' && (
            <div className="absolute right-0 mt-2 w-80 panel shadow-pop animate-slide-up">
              <div className="flex items-center justify-between px-4 py-3 border-b border-ink-700">
                <p className="text-sm font-semibold text-gray-200">Notifications</p>
                {items.length > 0 && (
                  <button onClick={clearBell} className="text-xs text-gray-500 hover:text-gray-300">
                    Clear all
                  </button>
                )}
              </div>
              <div className="max-h-80 overflow-y-auto">
                {items.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-8">Nothing yet</p>
                ) : (
                  items.map((item) => (
                    <div key={item.id} className="flex items-start gap-2.5 px-4 py-3 border-b border-ink-800 last:border-0">
                      <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${dotColor[item.type] || 'bg-gray-500'}`} />
                      <div className="min-w-0">
                        <p className="text-sm text-gray-300">{item.message}</p>
                        <p className="text-[11px] text-gray-600 mt-0.5">
                          {item.timestamp.toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <div ref={userRef} className="relative">
          <button
            onClick={() => toggle('user')}
            className="flex items-center gap-2 p-1 rounded-lg hover:bg-ink-800"
            aria-label="Account menu"
          >
            <div className="w-7 h-7 bg-brand-600 rounded-full grid place-items-center">
              <span className="text-white text-[11px] font-semibold">
                {getInitials(user?.email)}
              </span>
            </div>
          </button>

          {menu === 'user' && (
            <div className="absolute right-0 mt-2 w-60 panel shadow-pop py-1 animate-slide-up">
              <div className="px-4 py-3 border-b border-ink-700">
                <p className="text-sm text-gray-200 truncate">{user?.email}</p>
                <p className="text-[11px] text-gray-500 mt-0.5">{user?.role || 'user'}</p>
              </div>
              <button
                onClick={() => { navigate('/api-keys'); setMenu(null); }}
                className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-gray-300 hover:bg-ink-800"
              >
                <Key className="w-4 h-4" /> API Keys
              </button>
              <button
                onClick={() => { navigate('/settings'); setMenu(null); }}
                className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-gray-300 hover:bg-ink-800"
              >
                <Settings className="w-4 h-4" /> Settings
              </button>
              <div className="my-1 border-t border-ink-700" />
              <button
                onClick={() => { logout(); navigate('/login'); }}
                className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-bad hover:bg-bad/10"
              >
                <LogOut className="w-4 h-4" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
