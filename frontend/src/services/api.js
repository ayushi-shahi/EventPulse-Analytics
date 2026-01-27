import { API_CONFIG } from '../config';

/**
 * API Client with error handling and token management
 */
class APIClient {
  constructor() {
    this.baseURL = API_CONFIG.BASE_URL;
    this.timeout = API_CONFIG.TIMEOUT;
  }

  /**
   * Get auth token from localStorage
   */
  getToken() {
    return localStorage.getItem('token');
  }

  /**
   * Get API key from localStorage
   */
  getAPIKey() {
    return localStorage.getItem('selected_api_key');
  }

  /**
   * Set auth token
   */
  setToken(token) {
    localStorage.setItem('token', token);
  }

  /**
   * Remove auth token
   */
  removeToken() {
    localStorage.removeItem('token');
  }

  /**
   * Build headers
   */
  getHeaders(useAPIKey = false) {
    const headers = {
      'Content-Type': 'application/json',
    };

    if (useAPIKey) {
      const apiKey = this.getAPIKey();
      if (apiKey) {
        headers['X-API-Key'] = apiKey;
      }
    } else {
      const token = this.getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    return headers;
  }

  /**
   * Make HTTP request
   */
  async request(endpoint, options = {}) {
    const { 
      method = 'GET', 
      body = null, 
      headers = {}, 
      useAPIKey = false,
      signal = null,
    } = options;

    const url = `${this.baseURL}${endpoint}`;
    const defaultHeaders = this.getHeaders(useAPIKey);

    const config = {
      method,
      headers: { ...defaultHeaders, ...headers },
      signal,
    };

    if (body && method !== 'GET') {
      config.body = JSON.stringify(body);
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(url, {
        ...config,
        signal: signal || controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle 401 Unauthorized
      if (response.status === 401) {
        this.removeToken();
        window.location.href = '/login';
        throw new Error('Session expired. Please login again.');
      }

      // Parse response
      const contentType = response.headers.get('content-type');
      let data;

      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Request failed');
      }

      return data;
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }

  // ==================== AUTH ====================

  async register(email, password) {
    return this.request('/auth/register', {
      method: 'POST',
      body: { email, password, role: 'user' },
    });
  }

  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    this.setToken(data.access_token);
    return data;
  }

  async refreshToken(refreshToken) {
    const data = await this.request('/auth/refresh', {
      method: 'POST',
      body: { refresh_token: refreshToken },
    });
    this.setToken(data.access_token);
    return data;
  }

  async getCurrentUser() {
    return this.request('/auth/me');
  }

  async logout() {
    this.removeToken();
  }

  // ==================== API KEYS ====================

  async createAPIKey(clientName, rateLimit = 1000) {
    return this.request('/api-keys/', {
      method: 'POST',
      body: { client_name: clientName, rate_limit: rateLimit },
    });
  }

  async getAPIKeys() {
    return this.request('/api-keys/');
  }

  async getAPIKey(keyId) {
    return this.request(`/api-keys/${keyId}`);
  }

  async revokeAPIKey(keyId) {
    return this.request(`/api-keys/${keyId}/revoke`, {
      method: 'PATCH',
    });
  }

  async deleteAPIKey(keyId) {
    return this.request(`/api-keys/${keyId}`, {
      method: 'DELETE',
    });
  }

  // ==================== METRICS ====================

  async getOverviewMetrics(period = 'last_hour') {
    return this.request(`/metrics/overview?period=${period}`, {
      useAPIKey: true,
    });
  }

  async getTimeSeries(metricName, startTime, endTime, interval = '1m') {
    const params = new URLSearchParams({
      interval,
    });
    
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);

    return this.request(`/metrics/time-series/${metricName}?${params}`, {
      useAPIKey: true,
    });
  }

  async getTopEvents(period = 'last_hour', limit = 10) {
    return this.request(`/metrics/top-events?period=${period}&limit=${limit}`, {
      useAPIKey: true,
    });
  }

  async getActiveUsers(window = '1h') {
    return this.request(`/metrics/active-users?window=${window}`, {
      useAPIKey: true,
    });
  }

  async getEvents(params = {}) {
    const queryParams = new URLSearchParams();
    
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined) {
        queryParams.append(key, params[key]);
      }
    });

    return this.request(`/metrics/events?${queryParams}`, {
      useAPIKey: true,
    });
  }

  // ==================== ALERTS ====================

  async createAlert(alertData) {
    return this.request('/alerts/', {
      method: 'POST',
      body: alertData,
      useAPIKey: true,
    });
  }

  async getAlerts(enabled = null) {
    const params = enabled !== null ? `?enabled=${enabled}` : '';
    return this.request(`/alerts/${params}`, {
      useAPIKey: true,
    });
  }

  async getAlert(alertId) {
    return this.request(`/alerts/${alertId}`, {
      useAPIKey: true,
    });
  }

  async updateAlert(alertId, updates) {
    return this.request(`/alerts/${alertId}`, {
      method: 'PATCH',
      body: updates,
      useAPIKey: true,
    });
  }

  async deleteAlert(alertId) {
    return this.request(`/alerts/${alertId}`, {
      method: 'DELETE',
      useAPIKey: true,
    });
  }

  async testAlert(alertId) {
    return this.request(`/alerts/${alertId}/test`, {
      method: 'POST',
      useAPIKey: true,
    });
  }

  async getAlertHistory(alertId, limit = 50) {
    return this.request(`/alerts/${alertId}/history?limit=${limit}`, {
      useAPIKey: true,
    });
  }

  async enableAlert(alertId) {
    return this.request(`/alerts/${alertId}/enable`, {
      method: 'POST',
      useAPIKey: true,
    });
  }

  async disableAlert(alertId) {
    return this.request(`/alerts/${alertId}/disable`, {
      method: 'POST',
      useAPIKey: true,
    });
  }

  // ==================== INGESTION ====================

  async ingestEvent(eventData) {
    return this.request('/ingest/events', {
      method: 'POST',
      body: eventData,
      useAPIKey: true,
    });
  }

  async ingestEventBatch(events) {
    return this.request('/ingest/events/batch', {
      method: 'POST',
      body: { events },
      useAPIKey: true,
    });
  }

  async getIngestionStatus() {
    return this.request('/ingest/status', {
      useAPIKey: true,
    });
  }

  // ==================== HEALTH ====================

  async getHealth() {
    return this.request('/health/');
  }

  async getDetailedHealth() {
    return this.request('/health/detailed');
  }
}

// Export singleton instance
const apiClient = new APIClient();
export default apiClient;