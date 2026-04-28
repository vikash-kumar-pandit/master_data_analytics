const host = window.location.hostname || '127.0.0.1';
const isLocalHost = host === '127.0.0.1' || host === 'localhost';
const protocol = isLocalHost ? 'http' : 'https';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || `${protocol}://${host}:8000`;
