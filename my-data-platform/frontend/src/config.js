const host = window.location.hostname || '127.0.0.1';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || `http://${host}:8000`;
