from datetime import UTC, datetime, timedelta

from mona_core.db import Anomaly, Metric

class TestDashboardAndMetrics:
    def test_db_metrics_empty(self, client, mock_user_auth):
        resp = client.get("/api/v1/db-metrics")
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "next_cursor": None}

    def test_db_metrics_filter_by_device(self, client, db_session, mock_user_auth):
        db_session.add_all(
            [
                Metric(cpu=10, ram=20, device="srv-1"),
                Metric(cpu=30, ram=40, device="srv-2"),
            ]
        )
        db_session.commit()

        resp = client.get("/api/v1/db-metrics", params={"device": "srv-1"})
        body = resp.json()
        assert len(body) == 2
        assert body["items"][0]["device"] == "srv-1"

    def test_dashboard_combines_metrics_anomalies_and_model(
        self, client, db_session, mock_user_auth
    ):
        now = datetime.now(UTC)
        db_session.add_all(
            [
                Metric(cpu=50, ram=60, device="srv-1", timestamp=now),
                Anomaly(
                    metric_id=1,
                    cpu=95,
                    ram=90,
                    timestamp=now,
                    reason="cpu_spike",
                    score=0.99,
                    device="srv-1",
                ),
            ]
        )
        db_session.commit()

        resp = client.get("/api/v1/dashboard", params={"hours": 1})
        assert resp.status_code == 200
        body = resp.json()

        assert "srv-1" in body["devices"]
        assert len(body["metrics"]) == 1
        assert len(body["anomalies"]) == 1
        assert body["model"] is None

    def test_dashboard_respects_time_window(self, client, db_session, mock_user_auth):
        old = datetime.now(UTC) - timedelta(hours=5)
        db_session.add(Metric(cpu=1, ram=1, device="srv-1", timestamp=old))
        db_session.commit()

        resp = client.get("/api/v1/dashboard", params={"hours": 1})
        assert resp.json()["metrics"] == []
