"""
Load test configuration for my-data-platform using Locust.
Run: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""
from __future__ import annotations

import json
import random
from locust import HttpUser, TaskSet, task, between


SAMPLE_ROWS = [
    {"id": i, "name": f"item_{i}", "amount": float(i * 10), "date": "2024-01-15", "category": random.choice(["A", "B", "C"])}
    for i in range(1, 51)
]


class DataPlatformUser(HttpUser):
    wait_time = between(1, 4)

    def on_start(self):
        login_resp = self.client.post(
            "/api/auth/login",
            data={"username": "guest_viewer", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if login_resp.status_code == 200:
            self.token = login_resp.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(4)
    def analytics_query(self):
        if not self.token:
            return
        self.client.post(
            "/api/analytics/query",
            json={
                "question": "What is the total amount?",
                "rows": SAMPLE_ROWS,
            },
            headers=self.headers,
        )

    @task(2)
    def forecast_metric(self):
        if not self.token:
            return
        self.client.post(
            "/api/analytics/forecast",
            json={
                "rows": SAMPLE_ROWS,
                "metric_column": "amount",
                "horizon": 7,
            },
            headers=self.headers,
        )

    @task(2)
    def compare_versions(self):
        if not self.token:
            return
        self.client.post(
            "/api/analytics/compare",
            json={
                "before_rows": SAMPLE_ROWS,
                "after_rows": SAMPLE_ROWS[:30],
            },
            headers=self.headers,
        )

    @task(1)
    def data_quality_score(self):
        if not self.token:
            return
        self.client.post(
            "/api/quality/score",
            json={"rows": SAMPLE_ROWS},
            headers=self.headers,
        )

    @task(1)
    def list_catalog(self):
        if not self.token:
            return
        self.client.get("/api/catalog?limit=20", headers=self.headers)
