import React, { useState, useEffect, useCallback } from 'react';
import { Bell, Plus, Edit2, Trash2, Play, Pause, TestTube, History } from 'lucide-react';
import { useAPIKey } from '../hooks/useAPIKey';
import { useNotification } from '../hooks/useNotification';
import apiClient from '../services/api';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import Input from '../components/common/Input';
import Select from '../components/common/Select';
import Badge from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import Spinner from '../components/common/Spinner';
import { formatDate } from '../utils/formatters';
import {
  METRIC_OPTIONS,
  OPERATOR_OPTIONS,
  SEVERITY_OPTIONS,
  SEVERITY_COLORS,
} from '../config';

/**
 * Alerts Management Page Component
 */
const Alerts = () => {
  const { selectedAPIKey, hasSelectedKey } = useAPIKey();
  const { success, error: showError, warning } = useNotification();

  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [editingAlert, setEditingAlert] = useState(null);
  const [alertHistory, setAlertHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    metric: 'events_per_minute',
    operator: '>',
    threshold: 1000,
    severity: 'warning',
    cooldown_seconds: 300,
    websocket_enabled: true,
    email_addresses: '',
  });

  const [formErrors, setFormErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  // Fetch alerts
  const fetchAlerts = useCallback(async () => {
    if (!hasSelectedKey) return;

    setLoading(true);
    try {
      const data = await apiClient.getAlerts();
      setAlerts(data);
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  }, [hasSelectedKey, showError]);

  useEffect(() => {
    if (hasSelectedKey) {
      fetchAlerts();
    }
  }, [hasSelectedKey, fetchAlerts]);

  // Handle form change
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    if (formErrors[name]) {
      setFormErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  // Validate form
  const validate = () => {
    const errors = {};

    if (!formData.name.trim()) {
      errors.name = 'Alert name is required';
    }

    if (!formData.threshold || formData.threshold <= 0) {
      errors.threshold = 'Threshold must be greater than 0';
    }

    if (!formData.cooldown_seconds || formData.cooldown_seconds < 0) {
      errors.cooldown_seconds = 'Cooldown must be 0 or greater';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Create alert
  const handleCreate = async () => {
    if (!validate()) return;

    setSubmitting(true);
    try {
      const alertData = {
        name: formData.name,
        description: formData.description || null,
        expression: {
          metric: formData.metric,
          operator: formData.operator,
          threshold: parseFloat(formData.threshold),
          window: '1m',
        },
        severity: formData.severity,
        enabled: true,
        notification_channels: {
          websocket: formData.websocket_enabled,
          email: formData.email_addresses
            ? formData.email_addresses.split(',').map((e) => e.trim())
            : null,
        },
        cooldown_seconds: parseInt(formData.cooldown_seconds),
      };

      await apiClient.createAlert(alertData);
      await fetchAlerts();
      setShowCreateModal(false);
      resetForm();
      success('Alert created successfully!');
    } catch (err) {
      showError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  // Update alert
  const handleUpdate = async () => {
    if (!validate() || !editingAlert) return;

    setSubmitting(true);
    try {
      const updates = {
        name: formData.name,
        description: formData.description || null,
        expression: {
          metric: formData.metric,
          operator: formData.operator,
          threshold: parseFloat(formData.threshold),
          window: '1m',
        },
        severity: formData.severity,
        notification_channels: {
          websocket: formData.websocket_enabled,
          email: formData.email_addresses
            ? formData.email_addresses.split(',').map((e) => e.trim())
            : null,
        },
        cooldown_seconds: parseInt(formData.cooldown_seconds),
      };

      await apiClient.updateAlert(editingAlert.id, updates);
      await fetchAlerts();
      setShowEditModal(false);
      setEditingAlert(null);
      resetForm();
      success('Alert updated successfully!');
    } catch (err) {
      showError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  // Delete alert
  const handleDelete = async (alertId, alertName) => {
    if (!window.confirm(`Are you sure you want to delete "${alertName}"? This will also delete all alert history.`)) {
      return;
    }

    try {
      await apiClient.deleteAlert(alertId);
      await fetchAlerts();
      success('Alert deleted successfully');
    } catch (err) {
      showError(err.message);
    }
  };

  // Toggle alert enabled/disabled
  const handleToggle = async (alert) => {
    try {
      if (alert.enabled) {
        await apiClient.disableAlert(alert.id);
        success(`Alert "${alert.name}" disabled`);
      } else {
        await apiClient.enableAlert(alert.id);
        success(`Alert "${alert.name}" enabled`);
      }
      await fetchAlerts();
    } catch (err) {
      showError(err.message);
    }
  };

  // Test alert
  const handleTest = async (alert) => {
    try {
      const result = await apiClient.testAlert(alert.id);
      
      if (result.would_trigger) {
        warning(
          `Alert would trigger! Current: ${result.current_value.toFixed(2)}, Threshold: ${result.threshold}`
        );
      } else {
        success(
          `Alert would NOT trigger. Current: ${result.current_value.toFixed(2)}, Threshold: ${result.threshold}`
        );
      }
    } catch (err) {
      showError(err.message);
    }
  };

  // View history
  const handleViewHistory = async (alert) => {
    setShowHistoryModal(true);
    setHistoryLoading(true);
    setEditingAlert(alert);

    try {
      const history = await apiClient.getAlertHistory(alert.id);
      setAlertHistory(history);
    } catch (err) {
      showError(err.message);
    } finally {
      setHistoryLoading(false);
    }
  };

  // Open edit modal
  const openEditModal = (alert) => {
    setEditingAlert(alert);
    setFormData({
      name: alert.name,
      description: alert.description || '',
      metric: alert.expression.metric,
      operator: alert.expression.operator,
      threshold: alert.expression.threshold,
      severity: alert.severity,
      cooldown_seconds: alert.cooldown_seconds,
      websocket_enabled: alert.notification_channels?.websocket || false,
      email_addresses: alert.notification_channels?.email
        ? alert.notification_channels.email.join(', ')
        : '',
    });
    setShowEditModal(true);
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      metric: 'events_per_minute',
      operator: '>',
      threshold: 1000,
      severity: 'warning',
      cooldown_seconds: 300,
      websocket_enabled: true,
      email_addresses: '',
    });
    setFormErrors({});
  };

  if (!hasSelectedKey) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-[400px]">
        <EmptyState
          icon={Bell}
          title="No API Key Selected"
          description="Please select an API key to manage alerts."
          actionLabel="Go to API Keys"
          onAction={() => (window.location.href = '/api-keys')}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
          <p className="text-gray-600 mt-1">
            Configure and manage alerts for {selectedAPIKey?.client_name}
          </p>
        </div>
        <Button
          variant="primary"
          icon={Plus}
          onClick={() => {
            resetForm();
            setShowCreateModal(true);
          }}
        >
          Create Alert
        </Button>
      </div>

      {/* Alerts List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner message="Loading alerts..." />
        </div>
      ) : alerts.length === 0 ? (
        <Card>
          <EmptyState
            icon={Bell}
            title="No Alerts"
            description="Create your first alert to get notified when metrics exceed thresholds."
            actionLabel="Create Alert"
            onAction={() => {
              resetForm();
              setShowCreateModal(true);
            }}
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:gap-6">
          {alerts.map((alert) => {
            const severityConfig = SEVERITY_COLORS[alert.severity];
            return (
              <Card key={alert.id} hover className="shadow-sm">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {alert.name}
                      </h3>
                      <Badge
                        variant={alert.enabled ? 'success' : 'default'}
                        size="sm"
                      >
                        {alert.enabled ? 'Enabled' : 'Disabled'}
                      </Badge>
                      <Badge variant={alert.severity} size="sm">
                        {alert.severity}
                      </Badge>
                    </div>

                    {alert.description && (
                      <p className="text-sm text-gray-600 mb-3">
                        {alert.description}
                      </p>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500 font-medium">Condition</p>
                        <p className="text-gray-900">
                          {alert.expression.metric} {alert.expression.operator}{' '}
                          {alert.expression.threshold}
                        </p>
                      </div>

                      <div>
                        <p className="text-gray-500 font-medium">Cooldown</p>
                        <p className="text-gray-900">
                          {alert.cooldown_seconds}s
                        </p>
                      </div>

                      <div>
                        <p className="text-gray-500 font-medium">Triggers</p>
                        <p className="text-gray-900">{alert.trigger_count}</p>
                      </div>

                      <div>
                        <p className="text-gray-500 font-medium">Last Triggered</p>
                        <p className="text-gray-900">
                          {alert.last_triggered
                            ? formatDate(alert.last_triggered, 'MMM dd, HH:mm')
                            : 'Never'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      variant="ghost"
                      size="sm"
                      icon={alert.enabled ? Pause : Play}
                      onClick={() => handleToggle(alert)}
                    />

                    <Button
                      variant="ghost"
                      size="sm"
                      icon={TestTube}
                      onClick={() => handleTest(alert)}
                    />

                    <Button
                      variant="ghost"
                      size="sm"
                      icon={History}
                      onClick={() => handleViewHistory(alert)}
                    />

                    <Button
                      variant="ghost"
                      size="sm"
                      icon={Edit2}
                      onClick={() => openEditModal(alert)}
                    />

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(alert.id, alert.name)}
                    >
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create/Edit Alert Modal */}
      <Modal
        isOpen={showCreateModal || showEditModal}
        onClose={() => {
          setShowCreateModal(false);
          setShowEditModal(false);
          setEditingAlert(null);
          resetForm();
        }}
        title={showEditModal ? 'Edit Alert' : 'Create New Alert'}
        size="lg"
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => {
                setShowCreateModal(false);
                setShowEditModal(false);
                setEditingAlert(null);
                resetForm();
              }}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={showEditModal ? handleUpdate : handleCreate}
              loading={submitting}
            >
              {showEditModal ? 'Update Alert' : 'Create Alert'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input
            label="Alert Name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="e.g., High Traffic Alert"
            error={formErrors.name}
            required
          />

          <Input
            label="Description (Optional)"
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Describe when this alert should trigger"
          />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Select
              label="Metric"
              name="metric"
              value={formData.metric}
              onChange={handleChange}
              options={METRIC_OPTIONS}
              required
            />

            <Select
              label="Operator"
              name="operator"
              value={formData.operator}
              onChange={handleChange}
              options={OPERATOR_OPTIONS}
              required
            />

            <Input
              label="Threshold"
              type="number"
              name="threshold"
              value={formData.threshold}
              onChange={handleChange}
              error={formErrors.threshold}
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Select
              label="Severity"
              name="severity"
              value={formData.severity}
              onChange={handleChange}
              options={SEVERITY_OPTIONS}
              required
            />

            <Input
              label="Cooldown (seconds)"
              type="number"
              name="cooldown_seconds"
              value={formData.cooldown_seconds}
              onChange={handleChange}
              helperText="Minimum time between alert triggers"
              error={formErrors.cooldown_seconds}
              required
            />
          </div>

          <div className="border-t border-gray-200 pt-4">
            <h4 className="text-sm font-medium text-gray-900 mb-3">
              Notification Channels
            </h4>

            <div className="space-y-3">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  name="websocket_enabled"
                  checked={formData.websocket_enabled}
                  onChange={handleChange}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  Send to WebSocket (Live Feed)
                </span>
              </label>

              <Input
                label="Email Addresses (comma-separated)"
                name="email_addresses"
                value={formData.email_addresses}
                onChange={handleChange}
                placeholder="admin@example.com, ops@example.com"
                helperText="Leave empty to disable email notifications"
              />
            </div>
          </div>
        </div>
      </Modal>

      {/* Alert History Modal */}
      <Modal
        isOpen={showHistoryModal}
        onClose={() => {
          setShowHistoryModal(false);
          setEditingAlert(null);
          setAlertHistory([]);
        }}
        title={`Alert History: ${editingAlert?.name || ''}`}
        size="xl"
      >
        {historyLoading ? (
          <div className="flex items-center justify-center py-8">
            <Spinner message="Loading history..." />
          </div>
        ) : alertHistory.length === 0 ? (
          <EmptyState
            icon={History}
            title="No History"
            description="This alert has not been triggered yet."
          />
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {alertHistory.map((record) => (
              <div
                key={record.id}
                className={`p-4 rounded-lg border ${
                  SEVERITY_COLORS[record.severity].bg
                } ${SEVERITY_COLORS[record.severity].border}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <Badge variant={record.severity} size="sm">
                    {record.severity}
                  </Badge>
                  <span className="text-xs text-gray-600">
                    {formatDate(record.triggered_at)}
                  </span>
                </div>

                <p className="text-sm text-gray-900 mb-2">{record.message}</p>

                {record.context && (
                  <div className="text-xs text-gray-600">
                    <span className="font-medium">Current Value:</span>{' '}
                    {record.context.current_value?.toFixed(2) || 'N/A'} |{' '}
                    <span className="font-medium">Threshold:</span>{' '}
                    {record.context.threshold || 'N/A'}
                  </div>
                )}

                <div className="mt-2">
                  <Badge
                    variant={record.notification_sent ? 'success' : 'warning'}
                    size="xs"
                  >
                    {record.notification_sent ? 'Notified' : 'Not Notified'}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Alerts;