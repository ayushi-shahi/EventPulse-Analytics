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
  const { selectAPIKey, updateAPIKeys } = useAPIKey();
  const { success, error: showError } = useNotification();

  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showNewKeyModal, setShowNewKeyModal] = useState(false);
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
      
      // Refresh keys list
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
      await fetchKeys();
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

  if (loading) {
    return <Spinner fullScreen message="Loading API keys..." />;
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
          <p className="text-gray-600 mt-1">
            Manage your API keys for event ingestion and analytics
          </p>
        </div>

        <Button
          variant="primary"
          icon={Plus}
          onClick={() => setShowCreateModal(true)}
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
        <div className="grid grid-cols-1 gap-6">
          {keys.map((key) => (
            <Card key={key.id} hover>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <Key className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {key.client_name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        Created {formatDate(key.created_at)}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase mb-1">
                        API Key ID
                      </p>
                      <div className="flex items-center gap-2">
                        <code className="text-sm font-mono text-gray-700 bg-gray-50 px-2 py-1 rounded">
                          {key.id}
                        </code>
                        <button
                          onClick={() => handleCopy(key.id, `id-${key.id}`)}
                          className="text-gray-400 hover:text-gray-600 transition-colors"
                        >
                          {copiedId === `id-${key.id}` ? (
                            <Check className="w-4 h-4 text-green-600" />
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
                      <p className="text-sm text-gray-700">
                        {key.rate_limit.toLocaleString()} requests/minute
                      </p>
                    </div>

                    <div className="md:col-span-2">
                      <p className="text-xs font-medium text-gray-500 uppercase mb-1">
                        Status
                      </p>
                      <Badge variant={key.is_active ? 'success' : 'danger'}>
                        {key.is_active ? 'Active' : 'Revoked'}
                      </Badge>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {key.is_active && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => selectAPIKey(key)}
                      >
                        Select
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRevoke(key.id, key.client_name)}
                      >
                        Revoke
                      </Button>
                    </>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(key.id, key.client_name)}
                  >
                    <Trash2 className="w-4 h-4 text-red-600" />
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
          <Button
            variant="primary"
            onClick={() => {
              setShowNewKeyModal(false);
              setNewKeyData(null);
            }}
          >
            I've Saved My API Key
          </Button>
        }
      >
        <div className="space-y-4">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex gap-3">
              <div className="flex-shrink-0">
                <svg className="w-5 h-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div>
                <h3 className="text-sm font-medium text-yellow-800">
                  Save this API key now!
                </h3>
                <p className="text-sm text-yellow-700 mt-1">
                  This is the only time you'll see the full API key. Store it securely.
                </p>
              </div>
            </div>
          </div>

          {newKeyData && (
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API Key
                </label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-sm font-mono bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 break-all">
                    {newKeyData.api_key}
                  </code>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleCopy(newKeyData.api_key, 'new-key')}
                  >
                    {copiedId === 'new-key' ? (
                      <Check className="w-4 h-4 text-green-600" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Client Name
                  </label>
                  <p className="text-sm text-gray-900">{newKeyData.client_name}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Rate Limit
                  </label>
                  <p className="text-sm text-gray-900">
                    {newKeyData.rate_limit.toLocaleString()} req/min
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default APIKeys;