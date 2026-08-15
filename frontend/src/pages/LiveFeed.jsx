import React, { useState, useEffect, useRef } from 'react';
import { Radio, Trash2, Download, AlertTriangle, X, Activity, Pause, Play } from 'lucide-react';
import { useAPIKey } from '../hooks/useAPIKey';
import { useWebSocket } from '../hooks/useWebSocket';
import { useNotification } from '../hooks/useNotification';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import { formatDate, formatJSON } from '../utils/formatters';
import { useNavigate } from "react-router-dom";

function eventsToCSV(events) {
  const headers = ['Timestamp', 'Event Name', 'User ID', 'Properties'];
  const rows = events.map((ev) => {
    const ts     = ev.timestamp || ev.data?.received_at;
    const name   = ev.data?.event_name || 'Unknown';
    const userId = ev.data?.user_id || '';
    const props  = ev.data?.properties
      ? JSON.stringify(ev.data.properties).replace(/"/g, '""')
      : '';
    return [formatDate(ts), name, userId, '"' + props + '"'];
  });
  return '\uFEFF' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\r\n');
}

const LiveFeed = () => {
  const { selectedAPIKey, hasSelectedKey } = useAPIKey();
  const {
    isConnected,
    events,
    totalEventsCount,
    currentAlert,
    rateLimitExceeded,
    connect,
    disconnect,
    clearEvents,
    dismissAlert,
    resetRateLimit,
  } = useWebSocket();
  const { success, error: showError } = useNotification();

  const [isPaused, setIsPaused]         = useState(false);
  const [pausedEvents, setPausedEvents] = useState([]);
  const [pausedCount, setPausedCount]   = useState(0);
  const [autoScroll, setAutoScroll]     = useState(true);
  const eventsContainerRef              = useRef(null);
  const navigate = useNavigate();

  // ─── Connection management ────────────────────────────────────────────────
  // Dep is selectedAPIKey?.id — fires only when the actual key changes,
  // not on every object re-reference. connect() in the context handles
  // hard-closing the old socket, bumping the generation counter (so stale
  // messages are dropped), clearing all event state, then opening the new
  // socket.  We only need to reset local pause state here.
  const prevKeyIdRef = useRef(selectedAPIKey?.id ?? null);

  useEffect(() => {
    const currentId  = selectedAPIKey?.id ?? null;
    const keyChanged = currentId !== prevKeyIdRef.current;
    prevKeyIdRef.current = currentId;

    if (keyChanged) {
      // Reset local pause snapshot — context already clears event arrays
      setIsPaused(false);
      setPausedEvents([]);
      setPausedCount(0);
    }

    // The provider owns the connection lifecycle now, so the socket is
    // already open before this page mounts. Only local pause state resets here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAPIKey?.id, hasSelectedKey]);
  // connect/disconnect are stable useCallback refs — excluding them from deps
  // prevents spurious reconnects on unrelated re-renders.

  // ─── Auto-pause on rate limit ─────────────────────────────────────────────
  useEffect(() => {
    if (rateLimitExceeded) setIsPaused(true);
  }, [rateLimitExceeded]);

  // ─── Freeze snapshot when pausing ────────────────────────────────────────
  // Only snapshot on the transition isPaused: false → true, not on every tick.
  const prevIsPausedRef = useRef(false);
  useEffect(() => {
    const wasRunning = !prevIsPausedRef.current;
    prevIsPausedRef.current = isPaused;

    if (isPaused && wasRunning) {
      setPausedEvents([...events]);
      setPausedCount(totalEventsCount);
    }
  }, [isPaused, events, totalEventsCount]);

  // ─── Auto-scroll ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (autoScroll && eventsContainerRef.current && !isPaused) {
      eventsContainerRef.current.scrollTop = eventsContainerRef.current.scrollHeight;
    }
  }, [events, autoScroll, isPaused]);

  const displayedEvents = isPaused ? pausedEvents : events;
  const displayedCount  = isPaused ? pausedCount  : totalEventsCount;

  // ─── Handlers ─────────────────────────────────────────────────────────────
  const handlePauseToggle = () => {
    if (rateLimitExceeded && !isPaused) {
      showError('Cannot resume — rate limit exceeded');
      return;
    }
    setIsPaused((prev) => !prev);
  };

  const handleExportCSV = () => {
    if (!displayedEvents.length) { showError('No events to export'); return; }
    const blob = new Blob([eventsToCSV(displayedEvents)], { type: 'text/csv;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `events-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    success('Events exported to CSV (Excel compatible)');
  };

  const handleClear = () => {
    if (!window.confirm('Are you sure you want to clear all events?')) return;
    clearEvents();
    setPausedEvents([]);
    setPausedCount(0);
    setIsPaused(false);
    success('Events cleared');
  };

  const handleDismissRateLimit = () => {
    resetRateLimit();
    setIsPaused(false);
    if (selectedAPIKey) {
      connect(
        selectedAPIKey.id,
        selectedAPIKey.api_key || selectedAPIKey.key || localStorage.getItem('token')
      );
    }
  };

  const getEventColor = (eventName) => {
    const colors = {
      page_view: 'bg-brand-600/15 border-l-4 border-l-blue-500',
      click:     'bg-ok/10 border-l-4 border-l-green-500',
      error:     'bg-bad/10 border-l-4 border-l-red-500',
      purchase:  'bg-viz-6/10 border-l-4 border-l-purple-500',
    };
    return colors[eventName] || ' border-l-4 border-l-gray-400';
  };

  // ─── No key selected ──────────────────────────────────────────────────────
  if (!hasSelectedKey) {
    return (
      <div className="min-h-screen -mt-[700px] flex items-center justify-center  px-4 py-8">
        <EmptyState
          icon={Radio}
          title="No API Key Selected"
          description="Please select an API key to view live events."
          actionLabel="Go to API Keys"
          onAction={() => navigate('/api-keys')}
        />
      </div>
    );
  }

  return (
    <div className="">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="space-y-4 sm:space-y-6">

          {/* ── Rate Limit Banner ─────────────────────────────────────────── */}
          {rateLimitExceeded && (
            <div className="animate-pulse-slow">
              <div className="bg-bad text-white rounded-xl p-5 sm:p-6 shadow-2xl border-4 border-bad">
                <div className="flex items-start gap-3 sm:gap-4">
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 sm:w-14 sm:h-14 bg-ink-900 rounded-xl flex items-center justify-center">
                      <AlertTriangle className="w-6 h-6 sm:w-8 sm:h-8 text-bad" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg sm:text-xl font-bold mb-2">🚫 Rate Limit Exceeded</h3>
                    <p className="text-sm sm:text-base text-bad mb-4">
                      Your API key has reached its request limit. Event stream has been paused
                      automatically. No new events will be recorded until the limit resets.
                    </p>
                    <div className="flex flex-wrap gap-2 sm:gap-3">
                      <Button
                        variant="outline" size="sm" onClick={handleDismissRateLimit}
                        className="bg-ink-900 text-bad hover:bg-bad/10 border-2 border-ink-700 font-semibold"
                      >
                        Clear Error & Resume
                      </Button>
                      <Button
                        variant="outline" size="sm"
                        onClick={() => (window.location.href = '/api-keys')}
                        className="bg-ink-900 text-bad hover:bg-bad/10 border-2 border-ink-700 font-semibold"
                      >
                        Manage API Keys
                      </Button>
                    </div>
                  </div>
                  <button
                    onClick={handleDismissRateLimit}
                    className="text-white hover:bg-bad/90 rounded-lg p-2 transition-colors flex-shrink-0"
                  >
                    <X className="w-5 h-5 sm:w-6 sm:h-6" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ── Alert Banner ──────────────────────────────────────────────── */}
          {currentAlert && !rateLimitExceeded && (
            <div className="animate-slide-down">
              <div className={`rounded-xl p-4 sm:p-5 shadow-lg border-l-8 ${
                currentAlert.severity === 'error' || currentAlert.severity === 'critical'
                  ? 'bg-bad/10 border-bad'
                  : currentAlert.severity === 'warning'
                  ? 'bg-warn/10 border-warn'
                  : 'bg-brand-600/15 border-brand-500'
              }`}>
                <div className="flex items-start justify-between gap-3 sm:gap-4">
                  <div className="flex items-start gap-3 sm:gap-4 flex-1 min-w-0">
                    <div className={`flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center ${
                      currentAlert.severity === 'error' || currentAlert.severity === 'critical'
                        ? 'bg-bad'
                        : currentAlert.severity === 'warning'
                        ? 'bg-warn'
                        : 'bg-brand-600'
                    }`}>
                      <AlertTriangle className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2">
                        <Badge
                          variant={
                            currentAlert.severity === 'error' || currentAlert.severity === 'critical'
                              ? 'danger'
                              : currentAlert.severity === 'warning'
                              ? 'warning'
                              : 'info'
                          }
                          size="sm"
                        >
                          {currentAlert.severity?.toUpperCase() || 'ALERT'}
                        </Badge>
                        <span className="text-sm sm:text-base font-bold text-gray-100 truncate">
                          {currentAlert.alert_name || 'Alert Triggered'}
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm text-gray-200 font-medium mb-2">
                        {currentAlert.message || 'Threshold condition met'}
                      </p>
                      {currentAlert.context && (
                        <div className="flex flex-wrap gap-3 sm:gap-4 text-xs text-gray-300">
                          {currentAlert.context.current_value != null && (
                            <span><span className="font-semibold">Current:</span> {currentAlert.context.current_value}</span>
                          )}
                          {currentAlert.context.threshold != null && (
                            <span><span className="font-semibold">Threshold:</span> {currentAlert.context.threshold}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={dismissAlert}
                    className="text-gray-400 hover:text-gray-100 hover:bg-ink-800/50 rounded-lg p-2 transition-colors flex-shrink-0"
                  >
                    <X className="w-4 h-4 sm:w-5 sm:h-5" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ── Header ───────────────────────────────────────────────────── */}
          <div className="bg-ink-900 rounded-xl shadow-sm border border-ink-700 p-5 sm:p-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-brand-600 rounded-xl flex items-center justify-center shadow-lg flex-shrink-0">
                  <Radio className="w-6 h-6 sm:w-7 sm:h-7 text-white" />
                </div>
                <div className="min-w-0 flex-1">
                  <h1 className="text-xl sm:text-2xl font-bold text-gray-100">Live Event Feed</h1>
                  <p className="text-sm sm:text-base text-gray-400 mt-0.5 truncate">
                    Real-time from{' '}
                    <span className="font-semibold text-brand-400">{selectedAPIKey?.client_name}</span>
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                <Badge
                  variant={rateLimitExceeded ? 'danger' : isPaused ? 'warning' : isConnected ? 'success' : 'danger'}
                  className="text-xs sm:text-sm px-3 py-1.5 sm:px-4 sm:py-2"
                >
                  {rateLimitExceeded ? '⚠ Rate Limited' : isPaused ? '⏸ Paused' : isConnected ? '● Live' : '○ Disconnected'}
                </Badge>
                <Button
                  variant={isPaused ? 'primary' : 'outline'} size="sm"
                  icon={isPaused ? Play : Pause}
                  onClick={handlePauseToggle}
                  disabled={!isConnected && !isPaused}
                >
                  <span className="hidden sm:inline">{isPaused ? 'Resume' : 'Pause'} Feed</span>
                  <span className="sm:hidden">{isPaused ? 'Resume' : 'Pause'}</span>
                </Button>
                <Button
                  variant="outline" size="sm" icon={Download}
                  onClick={handleExportCSV}
                  disabled={displayedEvents.length === 0}
                >
                  <span className="hidden sm:inline">Export CSV</span>
                  <span className="sm:hidden">Export</span>
                </Button>
                <Button
                  variant="outline" size="sm" icon={Trash2}
                  onClick={handleClear}
                  disabled={displayedEvents.length === 0}
                >
                  <span className="hidden sm:inline">Clear</span>
                  <span className="sm:hidden"><Trash2 className="w-4 h-4" /></span>
                </Button>
              </div>
            </div>
          </div>

          {/* ── Pause Banner ─────────────────────────────────────────────── */}
          {isPaused && !rateLimitExceeded && (
            <div className="bg-warn/10 border-2 border-warn/40 rounded-xl p-4 shadow-sm">
              <div className="flex items-start gap-3">
                <Pause className="w-5 h-5 text-warn flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm sm:text-base font-semibold text-warn">Event Stream Paused</h4>
                  <p className="text-xs sm:text-sm text-warn mt-1">
                    Events frozen at {displayedCount.toLocaleString()} total. Click "Resume Feed" to continue.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ── Stats ────────────────────────────────────────────────────── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <div className="bg-ink-900 rounded-xl shadow-sm border border-ink-700 p-4 sm:p-5 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
                <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${isPaused ? 'bg-warn' : 'bg-brand-600'}`}>
                  <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                </div>
                <p className="text-xs sm:text-sm font-semibold text-gray-500 uppercase">Total Events</p>
              </div>
              <p className="text-2xl sm:text-3xl font-bold text-gray-100">{displayedCount.toLocaleString()}</p>
              {isPaused && <p className="text-xs text-warn mt-1 font-medium">Frozen</p>}
            </div>

            <div className="bg-ink-900 rounded-xl shadow-sm border border-ink-700 p-4 sm:p-5 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
                <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  rateLimitExceeded ? 'bg-bad' : isPaused ? 'bg-warn' : isConnected ? 'bg-ok' : 'bg-bad'
                }`}>
                  <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 bg-ink-900 rounded-full" />
                </div>
                <p className="text-xs sm:text-sm font-semibold text-gray-500 uppercase">Status</p>
              </div>
              <p className="text-xl sm:text-2xl font-bold text-gray-100">
                {rateLimitExceeded ? 'Limited' : isPaused ? 'Paused' : isConnected ? 'Live' : 'Offline'}
              </p>
            </div>

            <div className="bg-ink-900 rounded-xl shadow-sm border border-ink-700 p-4 sm:p-5 hover:shadow-md transition-shadow">
              <p className="text-xs sm:text-sm font-semibold text-gray-500 uppercase mb-2 sm:mb-3">Auto Scroll</p>
              <label className="flex items-center gap-2 sm:gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  className="w-4 h-4 sm:w-5 sm:h-5 text-brand-400 rounded-lg focus:ring-2 focus:ring-brand-500 cursor-pointer"
                />
                <span className="text-xs sm:text-sm font-medium text-gray-300">
                  {autoScroll ? 'Enabled' : 'Disabled'}
                </span>
              </label>
            </div>

            <div className="bg-ink-900 rounded-xl shadow-sm border border-ink-700 p-4 sm:p-5 hover:shadow-md transition-shadow">
              <p className="text-xs sm:text-sm font-semibold text-gray-500 uppercase mb-2 sm:mb-3">Connection</p>
              <div className="flex items-center gap-2 sm:gap-3">
                <div className={`w-3 h-3 sm:w-4 sm:h-4 rounded-full flex-shrink-0 ${
                  isConnected && !rateLimitExceeded && !isPaused ? 'bg-ok animate-pulse' : 'bg-bad'
                }`} />
                <span className="text-xs sm:text-sm font-medium text-gray-300">
                  {isConnected && !rateLimitExceeded && !isPaused ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>

          {/* ── Event Stream ─────────────────────────────────────────────── */}
          <div className="bg-ink-900 rounded-xl shadow-sm border border-ink-700 overflow-hidden">
            <div className="border-b border-ink-700 px-5 sm:px-6 py-3 sm:py-4 ">
              <div className="flex items-center justify-between">
                <h2 className="text-base sm:text-lg font-bold text-gray-100">
                  Event Stream ({displayedEvents.length.toLocaleString()} displayed)
                </h2>
                {isPaused && <Badge variant="warning" size="sm">⏸ Paused</Badge>}
              </div>
            </div>

            <div
              ref={eventsContainerRef}
              className="h-[500px] sm:h-[600px] overflow-y-auto p-4 sm:p-6 space-y-3 sm:space-y-4 "
            >
              {displayedEvents.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full">
                  {isConnected && !rateLimitExceeded && !isPaused ? (
                    <>
                      <div className="w-16 h-16 sm:w-20 sm:h-20 bg-ink-700 rounded-full flex items-center justify-center mb-4 animate-pulse">
                        <Radio className="w-8 h-8 sm:w-10 sm:h-10 text-gray-500" />
                      </div>
                      <p className="text-base sm:text-lg font-medium text-gray-500">Waiting for events...</p>
                      <p className="text-xs sm:text-sm text-gray-500 mt-2">Events will appear here in real-time</p>
                    </>
                  ) : (
                    <>
                      <div className={`w-16 h-16 sm:w-20 sm:h-20 rounded-full flex items-center justify-center mb-4 ${
                        rateLimitExceeded ? 'bg-bad/20' : isPaused ? 'bg-warn/20' : 'bg-bad/20'
                      }`}>
                        {rateLimitExceeded || isPaused
                          ? <Pause className="w-8 h-8 sm:w-10 sm:h-10 text-warn" />
                          : <X className="w-8 h-8 sm:w-10 sm:h-10 text-bad" />
                        }
                      </div>
                      <p className="text-base sm:text-lg font-medium text-gray-300">
                        {rateLimitExceeded ? 'Rate limit exceeded' : isPaused ? 'Event stream paused' : 'Not connected'}
                      </p>
                      <p className="text-xs sm:text-sm text-gray-500 mt-2">
                        {rateLimitExceeded
                          ? 'No new events will be recorded'
                          : isPaused
                          ? 'Click Resume Feed to continue'
                          : 'Events will appear when connected'}
                      </p>
                    </>
                  )}
                </div>
              ) : (
                displayedEvents.map((event, index) => (
                  <div
                    key={event.id || index}
                    className={`rounded-xl p-4 sm:p-5 shadow-sm hover:shadow-md transition-all ${getEventColor(event.data?.event_name)}`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-0 mb-3">
                      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                        <Badge variant="default" size="sm" className="font-semibold">
                          {event.data?.event_name || 'Unknown Event'}
                        </Badge>
                        {event.data?.user_id && (
                          <span className="text-xs font-medium text-gray-400 bg-ink-900 px-2 sm:px-3 py-1 rounded-full">
                            User: {event.data.user_id}
                          </span>
                        )}
                      </div>
                      <span className="text-xs font-medium text-gray-500 whitespace-nowrap">
                        {formatDate(event.timestamp || event.data?.received_at)}
                      </span>
                    </div>
                    {event.data?.properties && Object.keys(event.data.properties).length > 0 && (
                      <details className="mt-3">
                        <summary className="text-xs font-semibold text-gray-300 cursor-pointer hover:text-gray-100 select-none">
                          📋 Properties ({Object.keys(event.data.properties).length})
                        </summary>
                        <pre className="mt-3 text-xs bg-ink-900 rounded-lg p-3 sm:p-4 overflow-x-auto border border-ink-700 font-mono">
                          {formatJSON(event.data.properties)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default LiveFeed;