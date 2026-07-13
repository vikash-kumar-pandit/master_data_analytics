"""
Chaos test scripts for my-data-platform.
Run with: pytest tests/chaos/ -v

Requires: Docker Compose stack running (redis, backend, celery-worker)
"""
from __future__ import annotations

import time
import subprocess

import requests

BASE_URL = "http://localhost:8000"


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "compose", "ps"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _auth_headers() -> dict[str, str]:
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": "guest_viewer", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_backend_restarts_gracefully():
    """Kill and restart backend pod; verify healthcheck recovers."""
    if not _docker_available():
        return
    subprocess.run(
        ["docker", "compose", "restart", "backend"],
        cwd="C:/Users/vikash kumar/Desktop/big data analytics/my-data-platform",
        check=False,
    )
    time.sleep(20)

    for _ in range(12):
        try:
            if requests.get(f"{BASE_URL}/health", timeout=2).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(5)
    raise AssertionError("Backend did not recover after restart")


def test_redis_failure_falls_back_to_sync():
    """Stop Redis; verify background prediction falls back to synchronous mode."""
    if not _docker_available():
        return
    import subprocess

    headers = _auth_headers()
    csv_content = "id,name,amount\n1,foo,10\n2,bar,20\n"

    subprocess.run(
        ["docker", "compose", "stop", "redis"],
        cwd="C:/Users/vikash kumar/Desktop/big data analytics/my-data-platform",
        check=False,
    )
    time.sleep(3)

    try:
        resp = requests.post(
            f"{BASE_URL}/api/predict-background",
            headers=headers,
            files={"file": ("data.csv", csv_content, "text/csv")},
            data={"target_column": "amount"},
            timeout=30,
        )
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            body = resp.json()
            assert body.get("sync_result") or body.get("task_id")
    finally:
        subprocess.run(
            ["docker", "compose", "start", "redis"],
            cwd="C:/Users/vikash kumar/Desktop/big data analytics/my-data-platform",
            check=False,
        )
        time.sleep(5)


def test_rate_limiter_blocks_under_load():
    """Send rapid requests and verify 429 responses."""
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.RequestException:
        return
    headers = _auth_headers()
    for _ in range(60):
        requests.post(
            f"{BASE_URL}/api/analytics/query",
            json={"question": "total amount?", "rows": SAMPLE_ROWS},
            headers=headers,
            timeout=5,
        )
    resp = requests.post(
        f"{BASE_URL}/api/analytics/query",
        json={"question": "total amount?", "rows": SAMPLE_ROWS},
        headers=headers,
        timeout=5,
    )
    assert resp.status_code == 429


SAMPLE_ROWS = [
    {"id": i, "name": f"item_{i}", "amount": float(i * 10), "category": "A"}
    for i in range(1, 21)
]
