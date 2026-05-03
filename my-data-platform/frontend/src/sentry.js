import * as Sentry from '@sentry/browser';

const dsn = import.meta.env.VITE_SENTRY_DSN || '';
if (dsn) {
  Sentry.init({ dsn, release: import.meta.env.VITE_APP_VERSION || undefined, tracesSampleRate: 0.05 });
}

export default Sentry;
