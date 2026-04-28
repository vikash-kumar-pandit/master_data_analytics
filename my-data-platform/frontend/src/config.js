const host = window.location.hostname || '127.0.0.1';
const isLocalHost = host === '127.0.0.1' || host === 'localhost';

// For local dev: use localhost:8000. For production: use env var or show warning.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (isLocalHost ? 'http://localhost:8000' : null);

if (!API_BASE_URL) {
  console.warn(
    'API_BASE_URL not configured for production. Set VITE_API_BASE_URL during build or provide a backend URL.'
  );
}
