from datetime import UTC, datetime, timedelta

from mona_core.db import Anomaly

class TestAnomalies:
    def _make_anomaly(self, device, timestamp, score=0.9):
        return Anomaly(
            metric_id=1,
            cpu=90.0,
            ram=80.0,
            timestamp=timestamp,
            reason="cpu_spike",
            score=score,
            device=device,
        )

    def test_get_anomalies_default_window(self, client, db_session, mock_user_auth):
        now = datetime.now(UTC)
        db_session.add_all(
            [
                self._make_anomaly("srv-1", now - timedelta(hours=1)),
                self._make_anomaly("srv-1", now - timedelta(hours=48)),
            ]
        )
        db_session.commit()

        resp = client.get("/api/v1/anomalies")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        assert body["items"][0]["device"] == "srv-1"

    def test_get_anomalies_filter_by_device(self, client, db_session, mock_user_auth):
        now = datetime.now(UTC)
        db_session.add_all(
            [
                self._make_anomaly("srv-1", now),
                self._make_anomaly("srv-2", now),
            ]
        )
        db_session.commit()

        resp = client.get("/api/v1/anomalies", params={"device": "srv-2"})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        assert body["items"][0]["device"] == "srv-2"

    def test_get_anomalies_hours_zero_disables_time_filter(
        self, client, db_session, mock_user_auth
    ):
        now = datetime.now(UTC)
        db_session.add(self._make_anomaly("srv-1", now - timedelta(days=30)))
        db_session.commit()

        resp = client.get("/api/v1/anomalies", params={"hours": 0})
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_get_anomalies_ordered_desc(self, client, db_session, mock_user_auth):
        now = datetime.now(UTC)
        db_session.add_all(
            [
                self._make_anomaly("srv-1", now - timedelta(minutes=10)),
                self._make_anomaly("srv-1", now - timedelta(minutes=1)),
            ]
        )
        db_session.commit()

        resp = client.get("/api/v1/anomalies")
        body = resp.json()
        timestamps = [a["timestamp"] for a in body["items"]]
        assert timestamps == sorted(timestamps, reverse=True)
