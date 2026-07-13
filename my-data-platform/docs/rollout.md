# Rollout Procedures

## Staging Smoke Test Checklist
1. Deploy latest image to staging namespace.
2. Wait for `/health` to return `{"status": "ok"}`.
3. Run curl sequence:
   - `POST /api/auth/login` → 200, return token.
   - `POST /upload` with small CSV → 200, return analysis + anomaly count.
   - `POST /clean` with same CSV → 200, return cleaned rows.
   - `POST /automl` with target column → 200, return model + accuracy.
   - `POST /api/analytics/forecast` → 200, return forecast points.
   - `POST /download` → 200, return ZIP with CSV + PDF + JSON.
   - `GET /api/catalog` → 200, list entries.
   - `POST /api/quality/anomalies` → 200, return anomaly report.
4. Verify Celery task completes in Flower (max 60s).
5. Verify Prometheus metrics endpoint returns non-empty family.
6. Sign off and promote to production.

## Production Canary
1. Deploy to production with `replicas: 2` and `maxSurge: 1`, `maxUnavailable: 0`.
2. Route 10% traffic to new pods via GKE Ingress or service mesh weights.
3. Monitor for 30 minutes:
   - Error rate < 1% (baseline from previous version).
   - p95 latency < 2s.
   - No 429 storms from new rate limiter.
   - Celery queue depth stable.
4. Pass → increase to 50%, then 100% in 15 min increments.
5. Fail → roll back to previous ReplicaSet.

## Post-Rollout Validation
1. Run full smoke test against production (same as staging).
2. Verify backup job completed successfully in the last 24h.
3. Verify Sentry captured at least one event (test release).
4. Check disk usage on PVCs < 70%.
5. Confirm Redis memory usage < 80%.
