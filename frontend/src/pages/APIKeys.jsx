import React, { useState, useEffect } from 'react';
import { Key, Plus, Trash2, Copy, Check, Eye, EyeOff } from 'lucide-react';
import { useAPIKey } from '../hooks/useAPIKey';
import { useNotification } from '../hooks/useNotification';
import apiClient from '../services/api';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import Input from '../components/common/Input';
import Badge from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import Spinner from '../components/common/Spinner';
import { formatDate, formatAPIKey, copyToClipboard } from '../utils/formatters';

/**
 * API Keys Management Page
 */
const APIKeys = () => {
  const { selectedAPIKey, selectAPIKey, updateAPIKeys, clearAPIKey } = useAPIKey();
  const { success, error: showError } = useNotification();

  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showNewKeyModal, setShowNewKeyModal] = useState(false);
  const [showEnterExistingKeyModal, setShowEnterExistingKeyModal] = useState(false);
  const [enterExistingKeyTarget, setEnterExistingKeyTarget] = useState(null);
  const [enteredExistingKey, setEnteredExistingKey] = useState('');
  const [newKeyData, setNewKeyData] = useState(null);
  const [formData, setFormData] = useState({
    client_name: '',
    rate_limit: 1000,
  });
  const [formErrors, setFormErrors] = useState({});
  const [creating, setCreating] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [visibleKeys, setVisibleKeys] = useState({});

  // Fetch API keys
  const fetchKeys = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getAPIKeys();
      setKeys(data);
      updateAPIKeys(data);
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  // Handle form change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (formErrors[name]) {
      setFormErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  // Validate form
  const validate = () => {
    const errors = {};

    if (!formData.client_name || formData.client_name.trim() === '') {
      errors.client_name = 'Client name is required';
    }

    if (!formData.rate_limit || formData.rate_limit < 1) {
      errors.rate_limit = 'Rate limit must be at least 1';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Create new API key
  const handleCreate = async () => {
    if (!validate()) return;

    setCreating(true);
    try {
      const data = await apiClient.createAPIKey(
        formData.client_name,
        parseInt(formData.rate_limit)
      );

      setNewKeyData(data);
      setShowCreateModal(false);
      setShowNewKeyModal(true);
      setFormData({ client_name: '', rate_limit: 1000 });

      // Persist the secret locally keyed by id
      try {
        const existing = JSON.parse(localStorage.getItem('api_key_secret_by_id') || '{}');
        existing[data.id] = data.api_key;
        localStorage.setItem('api_key_secret_by_id', JSON.stringify(existing));
      } catch {
        // ignore localStorage errors
      }
      
      await fetchKeys();
      success('API key created successfully!');
    } catch (err) {
      showError(err.message);
    } finally {
      setCreating(false);
    }
  };

  // Delete API key
  const handleDelete = async (keyId, clientName) => {
    if (!window.confirm(`Are you sure you want to delete the API key for "${clientName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await apiClient.deleteAPIKey(keyId);
      setKeys((prev) => {
        const next = prev.filter((key) => key.id !== keyId);
        updateAPIKeys(next);
        return next;
      });

      // Remove stored secret
      try {
        const map = JSON.parse(localStorage.getItem('api_key_secret_by_id') || '{}');
        if (map[keyId]) {
          delete map[keyId];
          localStorage.setItem('api_key_secret_by_id', JSON.stringify(map));
        }
      } catch {
        // ignore localStorage issues
      }

      if (selectedAPIKey?.id === keyId) {
        clearAPIKey();
      }

      success('API key deleted successfully');
    } catch (err) {
      showError(err.message);
    }
  };

  // Revoke API key
  const handleRevoke = async (keyId, clientName) => {
    if (!window.confirm(`Are you sure you want to revoke the API key for "${clientName}"?`)) {
      return;
    }

    try {
      await apiClient.revokeAPIKey(keyId);
      await fetchKeys();

      if (selectedAPIKey?.id === keyId) {
        clearAPIKey();
      }

      success('API key revoked successfully');
    } catch (err) {
      showError(err.message);
    }
  };

  // Copy to clipboard
  const handleCopy = async (text, id) => {
    const copied = await copyToClipboard(text);
    if (copied) {
      setCopiedId(id);
      success('Copied to clipboard!');
      setTimeout(() => setCopiedId(null), 2000);
    } else {
      showError('Failed to copy to clipboard');
    }
  };

  // Toggle key visibility
  const toggleKeyVisibility = (keyId) => {
    setVisibleKeys((prev) => ({ ...prev, [keyId]: !prev[keyId] }));
  };

  const getStoredSecretForKeyId = (keyId) => {
    try {
      const map = JSON.parse(localStorage.getItem('api_key_secret_by_id') || '{}');
      return map[keyId] || null;
    } catch {
      return null;
    }
  };

  const startSelectKey = (key) => {
    if (!key?.id) return;
    const storedSecret = getStoredSecretForKeyId(key.id);
    if (storedSecret) {
      selectAPIKey({
        id: key.id,
        api_key: storedSecret,
        client_name: key.client_name,
      });
      success(`Selected API key: ${key.client_name}`);
      return;
    }

    setEnterExistingKeyTarget({ id: key.id, client_name: key.client_name });
    setEnteredExistingKey('');
    setShowEnterExistingKeyModal(true);
  };

  const confirmEnterExistingKey = () => {
    const target = enterExistingKeyTarget;
    const secret = (enteredExistingKey || '').trim();
    if (!target?.id) return;
    if (!secret) {
      showError('Please paste a valid API key value.');
      return;
    }

    try {
      const existing = JSON.parse(localStorage.getItem('api_key_secret_by_id') || '{}');
      existing[target.id] = secret;
      localStorage.setItem('api_key_secret_by_id', JSON.stringify(existing));
    } catch {
      // ignore localStorage errors
    }

    selectAPIKey({
      id: target.id,
      api_key: secret,
      client_name: target.client_name,
    });
    setShowEnterExistingKeyModal(false);
    setEnterExistingKeyTarget(null);
    setEnteredExistingKey('');
    success(`Selected API key: ${target.client_name}`);
  };

  if (loading) {
    return <Spinner fullScreen message="Loading API keys..." />;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      <div className="space-y-5 sm:space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-100">API Keys</h1>
            <p className="text-sm sm:text-base text-gray-400 mt-1">
              Manage your API keys for event ingestion and analytics
            </p>
          </div>

          <Button
            variant="primary"
            icon={Plus}
            onClick={() => setShowCreateModal(true)}
            className="w-full sm:w-auto"
          >
            Create API Key
          </Button>
        </div>

        {/* API Keys List */}
        {keys.length === 0 ? (
          <Card>
            <EmptyState
              icon={Key}
              title="No API Keys"
              description="Create your first API key to start ingesting events and viewing analytics."
              actionLabel="Create API Key"
              onAction={() => setShowCreateModal(true)}
            />
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:gap-6">
            {keys.map((key) => (
              <Card key={key.id} hover>
                <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 bg-brand-600/20 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Key className="w-5 h-5 text-brand-400" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-base sm:text-lg font-semibold text-gray-100 truncate">
                          {key.client_name}
                        </h3>
                        <p className="text-xs sm:text-sm text-gray-500">
                          Created {formatDate(key.created_at)}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 mt-4">
                      <div>
                        <p className="text-xs font-medium text-gray-500 uppercase mb-1">
                          API Key ID
                        </p>
                        <div className="flex items-center gap-2">
                          <code className="text-xs sm:text-sm font-mono text-gray-300  px-2 py-1 rounded truncate flex-1">
                            {key.id}
                          </code>
                          <button
                            onClick={() => handleCopy(key.id, `id-${key.id}`)}
                            className="text-gray-500 hover:text-gray-300 transition-colors flex-shrink-0"
                          >
                            {copiedId === `id-${key.id}` ? (
                              <Check className="w-4 h-4 text-ok" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>

                      <div>
                        <p className="text-xs font-medium text-gray-500 uppercase mb-1">
                          Rate Limit
                        </p>
                        <p className="text-xs sm:text-sm text-gray-300">
                          {key.rate_limit.toLocaleString()} requests/minute
                        </p>
                      </div>

                      <div className="sm:col-span-2">
                        <p className="text-xs font-medium text-gray-500 uppercase mb-1">
                          Status
                        </p>
                        <Badge variant={key.is_active ? 'success' : 'danger'}>
                          {key.is_active ? 'Active' : 'Revoked'}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap lg:flex-col items-center lg:items-end gap-2">
                    {key.is_active && (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => startSelectKey(key)}
                          className="flex-1 sm:flex-none lg:w-full"
                        >
                          Select
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRevoke(key.id, key.client_name)}
                          className="flex-1 sm:flex-none lg:w-full"
                        >
                          Revoke
                        </Button>
                      </>
                    )}

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(key.id, key.client_name)}
                      className="flex-1 sm:flex-none lg:w-full"
                    >
                      <Trash2 className="w-4 h-4 text-bad" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Create API Key Modal */}
        <Modal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          title="Create New API Key"
          footer={
            <>
              <Button variant="ghost" onClick={() => setShowCreateModal(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleCreate}
                loading={creating}
              >
                Create API Key
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <Input
              label="Client Name"
              name="client_name"
              value={formData.client_name}
              onChange={handleChange}
              placeholder="e.g., Mobile App, Website, Backend Service"
              error={formErrors.client_name}
              helperText="A friendly name to identify this API key"
              required
            />

            <Input
              label="Rate Limit (requests/minute)"
              type="number"
              name="rate_limit"
              value={formData.rate_limit}
              onChange={handleChange}
              placeholder="1000"
              error={formErrors.rate_limit}
              helperText="Maximum number of requests per minute"
              min="1"
              required
            />
          </div>
        </Modal>

        {/* New API Key Display Modal */}
        <Modal
          isOpen={showNewKeyModal}
          onClose={() => {
            setShowNewKeyModal(false);
            setNewKeyData(null);
          }}
          title="API Key Created Successfully"
          size="lg"
          closeOnOverlayClick={false}
          footer={
            <>
              <Button
                variant="primary"
                onClick={() => {
                  if (newKeyData) {
                    selectAPIKey({
                      id: newKeyData.id,
                      api_key: newKeyData.api_key,
                      client_name: newKeyData.client_name,
                    });
                  }
                  setShowNewKeyModal(false);
                  setNewKeyData(null);
                }}
              >
                Select This Key & Continue
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <div className="bg-warn/10 border border-warn/30 rounded-lg p-3 sm:p-4">
              <div className="flex gap-2 sm:gap-3">
                <div className="flex-shrink-0">
                  <svg className="w-5 h-5 text-warn" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-xs sm:text-sm font-medium text-warn">
                    Save this API key now!
                  </h3>
                  <p className="text-xs sm:text-sm text-warn mt-1">
                    This is the only time you'll see the full API key. Copy it and store it securely.
                  </p>
                </div>
              </div>
            </div>

            {newKeyData && (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    API Key
                  </label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-xs sm:text-sm font-mono  border border-ink-600 rounded-lg px-3 sm:px-4 py-2 sm:py-3 break-all">
                      {newKeyData.api_key}
                    </code>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCopy(newKeyData.api_key, 'new-key')}
                      className="flex-shrink-0"
                    >
                      {copiedId === 'new-key' ? (
                        <Check className="w-4 h-4 text-ok" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Client Name
                    </label>
                    <p className="text-sm text-gray-100">{newKeyData.client_name}</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Rate Limit
                    </label>
                    <p className="text-sm text-gray-100">
                      {newKeyData.rate_limit.toLocaleString()} req/min
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </Modal>

        {/* Enter Existing API Key Secret Modal */}
        <Modal
          isOpen={showEnterExistingKeyModal}
          onClose={() => {
            setShowEnterExistingKeyModal(false);
            setEnterExistingKeyTarget(null);
            setEnteredExistingKey('');
          }}
          title="Enter API Key"
          size="lg"
          footer={
            <>
              <Button
                variant="ghost"
                onClick={() => {
                  setShowEnterExistingKeyModal(false);
                  setEnterExistingKeyTarget(null);
                  setEnteredExistingKey('');
                }}
              >
                Cancel
              </Button>
              <Button variant="primary" onClick={confirmEnterExistingKey}>
                Save & Select
              </Button>
            </>
          }
        >
          <div className="space-y-3">
            <p className="text-xs sm:text-sm text-gray-400">
              For security, the backend only shows an API key once at creation. Paste the key value for{' '}
              <span className="font-medium text-gray-100">
                {enterExistingKeyTarget?.client_name || 'this client'}
              </span>
              .
            </p>
            <Input
              label="API Key"
              name="existing_api_key"
              value={enteredExistingKey}
              onChange={(e) => setEnteredExistingKey(e.target.value)}
              placeholder="Paste your API key here"
              helperText="This will be saved locally in your browser for future selections."
              required
            />
          </div>
        </Modal>
      </div>
    </div>
  );
};

export default APIKeys;