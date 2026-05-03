// Dynamically load @sentry/browser only when a DSN is configured.
// This avoids a hard dependency at build time (useful for local dev without the package).
let SentryInstance = null;
const dsn = import.meta.env.VITE_SENTRY_DSN || '';

if (dsn) {
  import('@sentry/browser')
    .then((mod) => {
      const Sentry = mod && (mod.default || mod);
      try {
        Sentry.init({
          dsn,
          release: import.meta.env.VITE_APP_VERSION || undefined,
          tracesSampleRate: 0.05,
        });
        SentryInstance = Sentry;
        console.info('Sentry initialized');
      } catch (e) {
        // Initialization failed — don't block the app
        // eslint-disable-next-line no-console
        console.warn('Sentry init failed', e);
      }
    })
    .catch((err) => {
      // Package not installed or dynamic import failed; continue without Sentry
      // eslint-disable-next-line no-console
      console.warn('Sentry package not available or failed to load:', err);
    });
}

export default {
  captureException: (err, ctx) => {
    if (SentryInstance && SentryInstance.captureException) {
      SentryInstance.captureException(err, ctx);
    } else {
      // eslint-disable-next-line no-console
      console.warn('captureException called but Sentry is not initialized', err);
    }
  },
  captureMessage: (msg) => {
    if (SentryInstance && SentryInstance.captureMessage) {
      SentryInstance.captureMessage(msg);
    } else {
      // eslint-disable-next-line no-console
      console.log(msg);
    }
  },
  isEnabled: () => !!SentryInstance,
};
