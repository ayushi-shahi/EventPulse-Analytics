import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Activity, Search, Download, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAPIKey } from '../hooks/useAPIKey';
import { useNotification } from '../hooks/useNotification';
import apiClient from '../services/api';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Select from '../components/common/Select';
import Badge from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import Spinner from '../components/common/Spinner';
import { formatDate, formatJSON } from '../utils/formatters';

/**
 * Events Browser Page Component
 */
const Events = () => {
  const { selectedAPIKey, hasSelectedKey } = useAPIKey();
  const { success, error: showError } = useNotification();

  const [events, setEvents]   = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 50,
    total: 0,
    total_pages: 0,
  });

  const [filters, setFilters] = useState({
    event_name: '',
    user_id:    '',
    start_time: '',
    end_time:   '',
  });

  const [expandedRows, setExpandedRows] = useState({});

  // ✅ FIX 2 & 3: Track the previous API key ID.
  //    When the selected key changes (or is cleared), wipe the current events
  //    list and reset pagination/filters before fetching for the new key.
  const prevKeyIdRef = useRef(selectedAPIKey?.id ?? null);

  useEffect(() => {
    const currentId = selectedAPIKey?.id ?? null;
    const prevId    = prevKeyIdRef.current;

    if (currentId !== prevId) {
      prevKeyIdRef.current = currentId;

      // Reset everything so the previous key's data never shows for the new key
      setEvents([]);
      setExpandedRows({});
      setPagination({ page: 1, page_size: 50, total: 0, total_pages: 0 });
      setFilters({ event_name: '', user_id: '', start_time: '', end_time: '' });
    }
  }, [selectedAPIKey]);

  // Fetch events — depends on key, page, page_size, and filters
  const fetchEvents = useCallback(async () => {
    if (!hasSelectedKey) return;

    setLoading(true);
    try {
      const params = {
        page:      pagination.page,
        page_size: pagination.page_size,
      };

      if (filters.event_name) params.event_name = filters.event_name;
      if (filters.user_id)    params.user_id    = filters.user_id;
      if (filters.start_time) params.start_time = new Date(filters.start_time).toISOString();
      if (filters.end_time)   params.end_time   = new Date(filters.end_time).toISOString();

      const data = await apiClient.getEvents(params);

      setEvents(data.items || []);
      setPagination({
        page:        data.page,
        page_size:   data.page_size,
        total:       data.total,
        total_pages: data.total_pages,
      });
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  }, [hasSelectedKey, pagination.page, pagination.page_size, filters, showError]);

  // Re-fetch whenever the key, page, or page_size change.
  // Filters are applied explicitly via the Apply button (see handleApplyFilters).
  useEffect(() => {
    if (hasSelectedKey) {
      fetchEvents();
    } else {
      // Key was deselected — clear the list immediately
      setEvents([]);
      setExpandedRows({});
      setPagination({ page: 1, page_size: 50, total: 0, total_pages: 0 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasSelectedKey, selectedAPIKey, pagination.page, pagination.page_size]);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const handleApplyFilters = () => {
    setPagination((prev) => ({ ...prev, page: 1 }));
    fetchEvents();
  };

  const handleClearFilters = () => {
    const cleared = { event_name: '', user_id: '', start_time: '', end_time: '' };
    setFilters(cleared);
    setPagination((prev) => ({ ...prev, page: 1 }));
    // fetchEvents will be called by the pagination useEffect after state settles;
    // call explicitly too in case page was already 1 (no state change → no effect)
    fetchEvents();
  };

  const goToPage = (page) => {
    setPagination((prev) => ({ ...prev, page }));
  };

  const nextPage = () => {
    if (pagination.page < pagination.total_pages) goToPage(pagination.page + 1);
  };

  const previousPage = () => {
    if (pagination.page > 1) goToPage(pagination.page - 1);
  };

  const toggleRow = (eventId) => {
    setExpandedRows((prev) => ({ ...prev, [eventId]: !prev[eventId] }));
  };

  const handleExport = () => {
    const headers = ['ID', 'Event Name', 'User ID', 'Event Time', 'Received At', 'Properties'];
    const rows = events.map((event) => [
      event.id,
      event.event_name,
      event.user_id || 'N/A',
      formatDate(event.event_time),
      formatDate(event.received_at),
      JSON.stringify(event.properties || {}),
    ]);

    const csv = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url  = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href     = url;
    link.download = `events-${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);

    success('Events exported to CSV!');
  };

  if (!hasSelectedKey) {
    return (
      <div className="max-w-7xl mx-auto -mt-[400px]">
        <EmptyState
          icon={Activity}
          title="No API Key Selected"
          description="Please select an API key to view events."
          actionLabel="Go to API Keys"
          onAction={() => (window.location.href = '/api-keys')}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 -mt-72">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Events</h1>
          <p className="text-gray-600 mt-1">
            Browse and filter events from{' '}
            <span className="font-semibold text-blue-600">
              {selectedAPIKey?.client_name}
            </span>
          </p>
        </div>

        <Button
          variant="outline"
          icon={Download}
          onClick={handleExport}
          disabled={events.length === 0}
        >
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Input
            label="Event Name"
            name="event_name"
            value={filters.event_name}
            onChange={handleFilterChange}
            placeholder="e.g., page_view"
            icon={Search}
          />
          <Input
            label="User ID"
            name="user_id"
            value={filters.user_id}
            onChange={handleFilterChange}
            placeholder="Filter by user"
          />
          <Input
            label="Start Time"
            type="datetime-local"
            name="start_time"
            value={filters.start_time}
            onChange={handleFilterChange}
          />
          <Input
            label="End Time"
            type="datetime-local"
            name="end_time"
            value={filters.end_time}
            onChange={handleFilterChange}
          />
        </div>

        <div className="flex items-center gap-3 mt-4">
          <Button variant="primary" onClick={handleApplyFilters}>
            Apply Filters
          </Button>
          <Button variant="outline" onClick={handleClearFilters}>
            Clear
          </Button>
        </div>
      </Card>

      {/* Events Table */}
      <Card
        title={`Events (${pagination.total.toLocaleString()} total)`}
        padding={false}
      >
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Spinner message="Loading events..." />
          </div>
        ) : events.length === 0 ? (
          <div className="py-12">
            <EmptyState
              icon={Activity}
              title="No Events Found"
              description="No events match your current filters. Try adjusting your search criteria."
            />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Event
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      User ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Event Time
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Received At
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {events.map((event) => (
                    <React.Fragment key={event.id}>
                      <tr className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <Badge variant="primary" size="sm">
                            {event.event_name}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {event.user_id || (
                            <span className="text-gray-400">N/A</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(event.event_time)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(event.received_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <button
                            onClick={() => toggleRow(event.id)}
                            className="text-blue-600 hover:text-blue-800 font-medium"
                          >
                            {expandedRows[event.id] ? 'Hide' : 'View'} Details
                          </button>
                        </td>
                      </tr>

                      {expandedRows[event.id] && (
                        <tr>
                          <td colSpan="5" className="px-6 py-4 bg-gray-50">
                            <div className="space-y-2">
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <p className="text-xs font-medium text-gray-500 uppercase">
                                    Event ID
                                  </p>
                                  <p className="text-sm text-gray-900 mt-1">{event.id}</p>
                                </div>
                                <div>
                                  <p className="text-xs font-medium text-gray-500 uppercase">
                                    Client ID
                                  </p>
                                  <p className="text-sm text-gray-900 mt-1 font-mono">
                                    {event.client_id}
                                  </p>
                                </div>
                              </div>

                              {event.properties &&
                                Object.keys(event.properties).length > 0 && (
                                  <div>
                                    <p className="text-xs font-medium text-gray-500 uppercase mb-2">
                                      Properties
                                    </p>
                                    <pre className="text-xs bg-white border border-gray-200 rounded p-3 overflow-x-auto">
                                      {formatJSON(event.properties)}
                                    </pre>
                                  </div>
                                )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-700">
                  Showing{' '}
                  <span className="font-medium">
                    {(pagination.page - 1) * pagination.page_size + 1}
                  </span>{' '}
                  to{' '}
                  <span className="font-medium">
                    {Math.min(pagination.page * pagination.page_size, pagination.total)}
                  </span>{' '}
                  of{' '}
                  <span className="font-medium">{pagination.total.toLocaleString()}</span>{' '}
                  results
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    icon={ChevronLeft}
                    onClick={previousPage}
                    disabled={pagination.page === 1}
                  >
                    Previous
                  </Button>

                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => {
                      let pageNum;
                      if (pagination.total_pages <= 5) {
                        pageNum = i + 1;
                      } else if (pagination.page <= 3) {
                        pageNum = i + 1;
                      } else if (pagination.page >= pagination.total_pages - 2) {
                        pageNum = pagination.total_pages - 4 + i;
                      } else {
                        pageNum = pagination.page - 2 + i;
                      }

                      return (
                        <button
                          key={pageNum}
                          onClick={() => goToPage(pageNum)}
                          className={`px-3 py-1 text-sm rounded ${
                            pagination.page === pageNum
                              ? 'bg-blue-600 text-white'
                              : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    iconPosition="right"
                    icon={ChevronRight}
                    onClick={nextPage}
                    disabled={pagination.page === pagination.total_pages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
};

export default Events;