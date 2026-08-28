from mona_core.db import  Device

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
