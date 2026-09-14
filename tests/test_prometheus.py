from mona_core.db import Device

class TestPrometheus:
    def test_prometheus_targets_only_active_with_ip(self, client, db_session):
        db_session.add_all(
            [
                Device(ip="10.0.0.1", name="active-1", is_active=True),
                Device(ip="10.0.0.2", name="inactive-1", is_active=False),
            ]
        )
        db_session.commit()

        resp = client.get("/api/prometheus/targets")
        assert resp.status_code == 200
        body = resp.json()

        assert len(body) == 1
        target = body[0]
        assert target["targets"] == ["10.0.0.1:9100"]
        assert target["labels"] == {
            "job": "active-1",
            "physical_pc": "true",
            "device_label": "active-1",
        }
