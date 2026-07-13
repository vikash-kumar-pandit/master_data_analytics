import axios from 'axios';

// Create API client
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    let token = null;
    try {
      const raw = sessionStorage.getItem('my_data_platform_auth') || localStorage.getItem('my_data_platform_auth');
      if (raw) {
        token = JSON.parse(raw)?.token;
      }
    } catch (e) {
      console.error("Error parsing token in apiClient", e);
    }
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Redirect to login
      sessionStorage.removeItem('my_data_platform_auth');
      localStorage.removeItem('my_data_platform_auth');
      window.location.href = '/login';
    }

    if (error.response?.status === 403) {
      console.error('Access forbidden');
    }

    if (error.response?.status === 404) {
      console.error('Resource not found');
    }

    if (error.response?.status >= 500) {
      console.error('Server error');
    }

    return Promise.reject(error.response?.data || error.message);
  }
);

// API service methods
export const apiService = {
  // Generic methods
  get: (url, config) => apiClient.get(url, config),
  post: (url, data, config) => apiClient.post(url, data, config),
  put: (url, data, config) => apiClient.put(url, data, config),
  patch: (url, data, config) => apiClient.patch(url, data, config),
  delete: (url, config) => apiClient.delete(url, config),

  // Auth endpoints
  auth: {
    login: (email, password) =>
      apiClient.post('/auth/login', { email, password }),
    register: (userData) =>
      apiClient.post('/auth/register', userData),
    logout: () =>
      apiClient.post('/auth/logout'),
    refresh: () =>
      apiClient.post('/auth/refresh'),
  },

  // User endpoints
  users: {
    getProfile: () =>
      apiClient.get('/users/me'),
    updateProfile: (data) =>
      apiClient.put('/users/me', data),
    getAll: (params) =>
      apiClient.get('/users', { params }),
    getById: (id) =>
      apiClient.get(`/users/${id}`),
    delete: (id) =>
      apiClient.delete(`/users/${id}`),
  },

  // Data endpoints
  data: {
    getDatasets: (params) =>
      apiClient.get('/data/datasets', { params }),
    getDatasetById: (id) =>
      apiClient.get(`/data/datasets/${id}`),
    createDataset: (data) =>
      apiClient.post('/data/datasets', data),
    updateDataset: (id, data) =>
      apiClient.put(`/data/datasets/${id}`, data),
    deleteDataset: (id) =>
      apiClient.delete(`/data/datasets/${id}`),
    uploadFile: (file, datasetId) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post(`/data/datasets/${datasetId}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
  },

  // Analytics endpoints
  analytics: {
    getMetrics: (params) =>
      apiClient.get('/analytics/metrics', { params }),
    getChartData: (id) =>
      apiClient.get(`/analytics/charts/${id}`),
    generateReport: (data) =>
      apiClient.post('/analytics/reports', data),
  },

  // Search
  search: {
    global: (query, params) =>
      apiClient.get('/search', { params: { ...params, q: query } }),
  },

  // Utility for uploading files with progress
  uploadFile: (file, endpoint, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post(endpoint, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(progress);
        }
      },
    });
  },

  // Utility for downloading files
  downloadFile: (url, filename) => {
    return apiClient.get(url, { responseType: 'blob' }).then((blob) => {
      const urlBlob = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = urlBlob;
      link.download = filename;
      link.click();
      window.URL.revokeObjectURL(urlBlob);
    });
  },
  // Generate structured report (PDF/PPTX) and return blob
  generateStructuredReport: (payload, outputFormat = 'pdf') => {
    return apiClient.post('/analytics/report', { ...payload, output_format: outputFormat }, { responseType: 'blob' });
  },
  // Data quality endpoints
  quality: {
    getReport: (payload) => apiClient.post('/quality/report', payload),
    getScore: (payload) => apiClient.post('/quality/score', payload),
  },
  // Forecast / predictive endpoints
  forecasting: {
    forecast: (payload) => apiClient.post('/analytics/forecast', payload),
  },
  // Scheduling endpoints
  schedule: {
    create: (payload) => apiClient.post('/schedule/create', payload),
    list: () => apiClient.post('/schedule/list'),
  },
  // Real-time insights helper (WebSocket wrapper)
  realtime: {
    connectInsights: ({ onMessage, onOpen, onClose, onError, path = '/ws' } = {}) => {
      try {
        const wsBase = (import.meta.env.VITE_WS_URL || API_BASE_URL.replace(/^http/, 'ws').replace(/\/api\/?$/, ''));
        const url = wsBase.endsWith('/') ? `${wsBase.slice(0, -1)}${path}` : `${wsBase}${path}`;
        const ws = new WebSocket(url);

        ws.onopen = (ev) => { if (onOpen) onOpen(ev); };
        ws.onmessage = (ev) => { if (onMessage) onMessage(ev); };
        ws.onclose = (ev) => { if (onClose) onClose(ev); };
        ws.onerror = (ev) => { if (onError) onError(ev); };

        return {
          socket: ws,
          close: () => ws.close(),
        };
      } catch (err) {
        return { error: err };
      }
    },
  },
};

export default apiService;
