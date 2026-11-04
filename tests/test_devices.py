from mona_core.db import  Device
from sqlalchemy.orm import Session

class TestDevices:
    def test_get_device_empty(self, client, mock_user_auth):
        resp = client.get("/api/v1/devices")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_device(self, client, mock_admin_auth):
        payload = {"ip": "192.168.1.10", "name": "office-pc-1", "is_active": True}
        resp = client.post("/api/v1/devices", json=payload)

        assert resp.status_code == 201
        assert resp.json() == {"status": "ok", "message": "Device created"}

        listed = client.get("/api/v1/devices").json()
        assert len(listed) == 1
        assert listed[0]["ip"] == payload["ip"]
        assert listed[0]["name"] == payload["name"]
        assert listed[0]["is_active"] is True

    def test_create_device_default_active(self, client, mock_admin_auth):
        payload = {"ip": "192.168.1.10", "name": "office-pc-1"}
        resp = client.post("/api/v1/devices", json=payload)
        assert resp.status_code == 201

        listed = client.get("/api/v1/devices").json()
        assert listed[0]["is_active"] is True

    def test_create_device_duplicate_name_conflict(self, client, mock_admin_auth):
        payload = {"ip": "10.0.0.1", "name": "dup-name"}
        first = client.post("/api/v1/devices", json=payload)
        assert first.status_code == 201

        second = client.post("/api/v1/devices", json={"ip": "10.0.0.2", "name": "dup-name"})
        assert second.status_code == 409
        assert second.json()["message"] == "Name already exists"

    def test_list_devices_after_create(self, client, mock_admin_auth):
        client.post("/api/v1/devices", json={"ip": "10.0.0.1", "name": "a"})
        client.post("/api/v1/devices", json={"ip": "10.0.0.2", "name": "b"})

        resp = client.get("/api/v1/devices")
        assert resp.status_code == 200
        names = {d["name"] for d in resp.json()}
        assert names == {"a", "b"}

    def test_delete_device_success(self, client, db_session, mock_admin_auth):
        dev = Device(ip="10.0.0.9", name="to-delete")
        db_session.add(dev)
        db_session.commit()
        db_session.refresh(dev)

        resp = client.delete(f"/api/v1/devices/{dev.id}")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "Device deleted"}

        resp2 = client.get("/api/v1/devices")
        assert resp2.json() == []

    def test_delete_device_not_found(self, client, mock_admin_auth):
        resp = client.delete("/api/v1/devices/99999")
        assert resp.status_code == 404
        assert resp.json()["message"] == "Device not found"

    def test_switch_status_active_to_inactive(self, client, db_session, make_device, mock_admin_auth):
        dev = make_device(is_active=True)

        resp = client.patch(f"/api/v1/devices/{dev.id}/status")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "Device status changed"}

        db_session.refresh(dev)
        assert dev.is_active is False

    def test_switch_status_inactive_to_active(self, client, db_session, make_device, mock_admin_auth):
        dev = make_device(is_active=False)

        resp = client.patch(f"/api/v1/devices/{dev.id}/status")

        assert resp.status_code == 200
        db_session.refresh(dev)
        assert dev.is_active is True

    def test_switch_status_twice_returns_to_original(self, client, db_session, make_device, mock_admin_auth):
        dev = make_device(is_active=True)

        assert client.patch(f"/api/v1/devices/{dev.id}/status").status_code == 200
        assert client.patch(f"/api/v1/devices/{dev.id}/status").status_code == 200

        db_session.refresh(dev)
        assert dev.is_active is True

    def test_switch_status_reflected_in_list(self, client, make_device, mock_admin_auth):
        dev = make_device(is_active=True)

        client.patch(f"/api/v1/devices/{dev.id}/status")

        listed = client.get("/api/v1/devices").json()
        assert len(listed) == 1
        assert listed[0]["id"] == dev.id
        assert listed[0]["is_active"] is False

    def test_switch_status_affects_only_target_device(self, client, db_session, make_device, mock_admin_auth):
        target = make_device(name="target", ip="10.0.0.1", is_active=True)
        other = make_device(name="other", ip="10.0.0.2", is_active=True)

        client.patch(f"/api/v1/devices/{target.id}/status")

        db_session.refresh(target)
        db_session.refresh(other)
        assert target.is_active is False
        assert other.is_active is True

    def test_switch_status_not_found(self, client, mock_admin_auth):
        resp = client.patch("/api/v1/devices/99999/status")

        assert resp.status_code == 404
        assert resp.json()["message"] == "Device not found"

    def test_switch_status_invalid_id(self, client, mock_admin_auth):
        resp = client.patch("/api/v1/devices/abc/status")

        assert resp.status_code == 422

    def test_switch_status_commit_error(self, client, db_session, make_device, mock_admin_auth, monkeypatch):
        dev = make_device(is_active=True)  # создаём до патча, иначе commit в фабрике тоже упадёт

        def broken_commit(self, *args, **kwargs):
            raise RuntimeError("db is down")

        monkeypatch.setattr(Session, "commit", broken_commit)

        resp = client.patch(f"/api/v1/devices/{dev.id}/status")

        assert resp.status_code == 500
        assert resp.json()["message"] == "Error during changing device status"

        # после rollback значение в БД не изменилось
        db_session.refresh(dev)
        assert dev.is_active is True

    def test_switch_status_forbidden_for_regular_user(self, client, db_session, make_device, mock_user_auth):
        dev = make_device(is_active=True)

        resp = client.patch(f"/api/v1/devices/{dev.id}/status")

        assert resp.status_code == 403

        db_session.refresh(dev)
        assert dev.is_active is True