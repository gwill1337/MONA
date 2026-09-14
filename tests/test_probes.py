
class TestProbes:
    def test_liveness_probe(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "alive"}

    def test_readiness_probe_ok(self, client, mock_redis):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ready"}

    def test_readiness_probe_db_down(self, client, monkeypatch):
        from sqlalchemy.orm import Session

        def broken_execute(self, *args, **kwargs):
            raise Exception("connection refused")

        monkeypatch.setattr(Session, "execute", broken_execute)

        resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["message"] == "Database unavailable"
