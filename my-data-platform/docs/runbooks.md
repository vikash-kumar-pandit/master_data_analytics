# Operational Runbooks

## Secret Rotation

### JWT_SECRET_KEY
1. Generate a new strong secret (32+ chars): `openssl rand -hex 32`
2. Update the secret in the secrets manager / Kubernetes Secret.
3. Redeploy backend with rolling update (zero downtime).
4. All existing JWTs become invalid immediately. Users must re-login.
5. Coordinate with support team to notify users of forced re-authentication.

### OPENAI_API_KEY
1. Generate a new key in the OpenAI dashboard.
2. Update the secret in the secrets manager / Kubernetes Secret.
3. Redeploy backend with rolling update. No user impact; in-flight LLM calls may briefly fail and fall back to rule-based insights.

### REDIS_URL
1. Provision a new Redis instance or rotate credentials.
2. Update the secret. Rolling redeploy.
3. Verify Celery workers reconnect and queue depth recovers.

## Backup & Restore

### Daily Backup
- CronJob runs at 02:00 UTC.
- Archives `backend/data/` into GCS bucket `my-data-platform-backups`.
- Retention: 30 days (automated lifecycle rule).

### Restore Procedure
1. Identify the backup date: `backup-YYYY-MM-DD.tar.gz`.
2. Download and extract to a safe directory.
3. Stop backend + celery-worker pods.
4. Replace `backend/data/` with restored contents.
5. Start pods and verify `/health` returns OK.
6. Smoke test: upload → clean → AutoML → export.

## Incident Response

### Celery Queue Full / Slow Processing
- Check `flower` dashboard at `http://flower:5555`.
- Scale `celery-worker` replicas horizontally.
- If Redis is at maxmemory, clear old task keys or increase limit.
- Enable `--max-tasks-per-child` to prevent memory leaks.

### High Error Rate / 5xx Spike
- Check backend pod logs for stack traces.
- Verify Redis connectivity and OpenAI API status.
- Roll back to previous image if error rate > 5% for > 2 minutes.
- Page on-call if data loss risk (failed uploads/cleaning).

### Disk Full
- Kubernetes eviction will terminate pods. Verify PVC expansion or increase node disk.
- Alert threshold: disk usage > 80%.
