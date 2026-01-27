import React, { useState, useEffect, useRef } from 'react';
import { Radio, Pause, Play, Trash2, Download } from 'lucide-react';
import { useAPIKey } from '../hooks/useAPIKey';
import { useWebSocket } from '../hooks/useWebSocket';
import { useNotification } from '../hooks/useNotification';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import { formatDate, formatJSON } from '../utils/formatters';

/**
 * Live Feed Page Component
 */
const LiveFeed = () => {
  const { selectedAPIKey, hasSelectedKey } = useAPIKey();
  const { isConnected, events, connect, disconnect, clearEvents } = useWebSocket();
  const { success, error: showError } = useNotification();

  const [isPaused, setIsPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const eventsContainerRef = useRef(null);

  // Connect WebSocket when API key is selected
  useEffect(() => {
    if (hasSelectedKey && selectedAPIKey) {
      connect(selectedAPIKey.id, selectedAPIKey.key);
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [hasSelectedKey, selectedAPIKey, connect, disconnect]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && eventsContainerRef.current && !isPaused) {
      eventsContainerRef.current.scrollTop = eventsContainerRef.current.scrollHeight;
    }
  }, [events, autoScroll, isPaused]);

  // Handle pause/resume
  const togglePause = () => {
    setIsPaused(!isPaused);
  };

  // Export events to JSON
  const handleExport = () => {
    const dataStr = JSON.stringify(events, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `events-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
    success('Events exported successfully!');
  };

  // Handle clear events
  const handleClear = () => {
    if (window.confirm('Are you sure you want to clear all events?')) {
      clearEvents();
      success('Events cleared');
    }
  };

  // Get event color based on type
  const getEventColor = (eventName) => {
    const colors = {
      page_view: 'bg-blue-50 border-blue-200 text-blue-700',
      click: 'bg-green-50 border-green-200 text-green-700',
      error: 'bg-red-50 border-red-200 text-red-700',
      purchase: 'bg-purple-50 border-purple-200 text-purple-700',
    };
    return colors[eventName] || 'bg-gray-50 border-gray-200 text-gray-700';
  };

  if (!hasSelectedKey) {
    return (
      <div className="max-w-7xl mx-auto">
        <EmptyState
          icon={Radio}
          title="No API Key Selected"
          description="Please select an API key to view live events."
          actionLabel="Go to API Keys"
          onAction={() => window.location.href = '/api-keys'}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live Event Feed</h1>
          <p className="text-gray-600 mt-1">
            Real-time stream of events from {selectedAPIKey?.client_name}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant={isConnected ? 'success' : 'danger'}>
            {isConnected ? '● Connected' : '○ Disconnected'}
          </Badge>

          <Button
            variant="outline"
            size="sm"
            icon={isPaused ? Play : Pause}
            onClick={togglePause}
          >
            {isPaused ? 'Resume' : 'Pause'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            icon={Download}
            onClick={handleExport}
            disabled={events.length === 0}
          >
            Export
          </Button>

          <Button
            variant="outline"
            size="sm"
            icon={Trash2}
            onClick={handleClear}
            disabled={events.length === 0}
          >
            Clear
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card padding={false}>
          <div className="p-4">
            <p className="text-sm text-gray-600">Total Events</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {events.length.toLocaleString()}
            </p>
          </div>
        </Card>

        <Card padding={false}>
          <div className="p-4">
            <p className="text-sm text-gray-600">Status</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {isPaused ? 'Paused' : 'Live'}
            </p>
          </div>
        </Card>

        <Card padding={false}>
          <div className="p-4">
            <p className="text-sm text-gray-600">Auto Scroll</p>
            <label className="flex items-center gap-2 mt-2">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Enabled</span>
            </label>
          </div>
        </Card>

        <Card padding={false}>
          <div className="p-4">
            <p className="text-sm text-gray-600">Connection</p>
            <div className="flex items-center gap-2 mt-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm text-gray-700">
                {isConnected ? 'Active' : 'Inactive'}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Events Feed */}
      <Card title="Event Stream" padding={false}>
        <div
          ref={eventsContainerRef}
          className="h-[600px] overflow-y-auto p-4 space-y-3"
        >
          {events.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              {isConnected
                ? 'Waiting for events...'
                : 'Not connected. Events will appear here when connected.'}
            </div>
          ) : (
            events.map((event, index) => (
              <div
                key={event.id || index}
                className={`border rounded-lg p-4 ${getEventColor(event.data?.event_name)}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="default" size="sm">
                      {event.data?.event_name || 'Unknown Event'}
                    </Badge>
                    {event.data?.user_id && (
                      <span className="text-xs text-gray-600">
                        User: {event.data.user_id}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-gray-500">
                    {formatDate(event.timestamp || event.data?.received_at)}
                  </span>
                </div>

                {event.data?.properties && Object.keys(event.data.properties).length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs font-medium text-gray-600 cursor-pointer hover:text-gray-800">
                      Properties ({Object.keys(event.data.properties).length})
                    </summary>
                    <pre className="mt-2 text-xs bg-white bg-opacity-50 rounded p-2 overflow-x-auto">
                      {formatJSON(event.data.properties)}
                    </pre>
                  </details>
                )}
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
};

export default LiveFeed;