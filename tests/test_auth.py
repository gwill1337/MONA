import pytest

from mona_core.db import Users

class TestAuth:
    def test_valid_login(self, client, db_session, mock_redis):
        admin = Users(username="admin")
        admin.set_password("123456")

        db_session.add(admin)
        db_session.commit()

        resp = client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "123456"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        assert "user_session" in resp.cookies

    def test_invalid_login(self, client, db_session, mock_redis):
        admin = Users(username="admin")
        admin.set_password("password123")

        db_session.add(admin)
        db_session.commit()

        resp = client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "123456"}
        )
        assert resp.status_code == 401
        assert resp.json()["message"] == "Invalid username or password"

    def test_auth_me(self, client, mock_user_auth):
        resp = client.get("/api/v1/auth/me")

        assert resp.status_code == 200
        assert resp.json() == {"authenticated": True}

    def test_valid_logout(self, client, mock_redis):
        client.cookies.set("admin_session", "session123")

        resp = client.post(
            "/api/v1/auth/logout",
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_password_hash(self):
        admin = Users(username="admin")

        admin.set_password("123456")

        assert admin.password_hash != "123456"
        assert admin.check_password("123456")
        assert not admin.check_password("qwerty")

    def test_password_hash_random_salt(self):
        a = Users(username="a")
        b = Users(username="b")

        a.set_password("123456")
        b.set_password("123456")

        assert a.password_hash != b.password_hash

    @pytest.mark.parametrize(
        "method, endpoint",
        [
            ("POST", "/api/v1/devices"),
            ("DELETE", "/api/v1/devices/1"),
            ("POST", "/api/v1/train?hours=1"),
            ("DELETE", "/api/v1/model"),
        ],
    )
    def test_admin_previliges_with_user(self, client, method, endpoint, mock_user_auth):
        resp = client.request(method, endpoint)

        assert resp.status_code == 403

    @pytest.mark.parametrize(
        "method, endpoint",
        [
            ("GET", "/api/v1/devices"),
            ("GET", "/api/v1/anomalies"),
            ("GET", "/api/v1/model-info"),
            ("GET", "/api/v1/dashboard"),
            ("GET", "/api/v1/db-metrics"),
            ("GET", "/api/v1/task-status/dummy-task-id-123"),
        ],
    )
    def test_user_previliges_with_user(
        self, client, method, endpoint, mock_user_auth, mock_celery
    ):
        resp = client.request(method, endpoint)

        assert resp.status_code == 200

    @pytest.mark.parametrize(
        "method, endpoint",
        [
            ("GET", "/api/v1/devices"),
            ("GET", "/api/v1/anomalies"),
            ("GET", "/api/v1/model-info"),
            ("GET", "/api/v1/dashboard"),
            ("GET", "/api/v1/db-metrics"),
            ("GET", "/api/v1/task-status/dummy-task-id-123"),
        ],
    )
    def test_user_previliges_with_admin(
        self, client, method, endpoint, mock_admin_auth, mock_celery
    ):
        resp = client.request(method, endpoint)

        assert resp.status_code == 200


class TestSecureEndpoints:
    @pytest.mark.parametrize(
        "method, endpoint",
        [
            # Auth
            ("GET", "/api/v1/auth/me"),
            # Devices
            ("GET", "/api/v1/devices"),
            ("POST", "/api/v1/devices"),
            ("DELETE", "/api/v1/devices/1"),
            # Model & Anomalies
            ("GET", "/api/v1/anomalies"),
            ("GET", "/api/v1/model-info"),
            ("POST", "/api/v1/train?hours=1"),
            ("DELETE", "/api/v1/model"),
            # Dashboard & Metrics
            ("GET", "/api/v1/dashboard"),
            ("GET", "/api/v1/db-metrics"),
            # Tasks
            ("GET", "/api/v1/task-status/dummy-task-id-123"),
        ],
    )
    def test_endpoints_without_cookie_return_401(self, client, method, endpoint):
        resp = client.request(method, endpoint)

        assert resp.status_code == 401

class TestRateLimiter:
    def test_login_rate_limit_exceeded(self, client, db_session, mock_redis):
        admin = Users(username="admin")
        admin.set_password("correct_password")
        db_session.add(admin)
        db_session.commit()

        responses = []

        for _ in range(10):
            resp = client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrong_password"}
            )
            responses.append(resp)

        assert any(r.status_code == 429 for r in responses)
        
        last_resp = responses[-1]
        assert last_resp.status_code == 429

    def test_successful_login_resets_rate_limit(self, client, db_session, mock_redis):
        admin = Users(username="admin")
        admin.set_password("123456")
        db_session.add(admin)
        db_session.commit()

        for _ in range(2):
            client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrong_password"}
            )

        assert any("user:admin" in key or "ip:" in key for key in mock_redis.storage)

        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "123456"}
        )
        assert resp.status_code == 200

        assert mock_redis.storage.get("user:admin") is None

    def test_rate_limit_per_user(self, client, db_session, mock_redis):
        mock_redis.storage["login_attempts:user:target_user"] = 5

        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "target_user", "password": "some_password"}
        )

        assert resp.status_code == 429

class TestValidation:
    @pytest.mark.parametrize(
        "ip, name",
        [
            ("10.0.0", "test"),
            ("10", "test-10"),
            ("test", "srv-10"),
            ("2001:db8::1::2", "pc-12"),
            ("gggg::1", "srv-ipv6"),
            ("12345::1", "test-ipv6"),
        ],
    )
    def test_create_device_invalid_ip(self, client, ip, name, mock_admin_auth):
        payload = {"ip": ip, "name": name, "is_active": True}
        resp = client.post("/api/v1/devices", json=payload)

        assert resp.status_code == 422
        assert (
            resp.json()["detail"][0]["msg"]
            == "Value error, Must be a valid IPv4 or IPv6 address"
        )

    @pytest.mark.parametrize(
        "ip, name",
        [
            ("172.16.0.5", "{1==1}"),
            ("10.0.1.10", "bad_u$er}"),
            ("192.168.0.10", "} job {"),
            ("::1", "pc 12"),
            ("2001:db8::ff00:42:8329", "1234567890101112"),
            ("2001:0db8:0000:0000:0000:8a2e:0370:7334", "SRV-123456789101111"),
        ],
    )
    def test_create_device_invalid_name(self, ip, name, client, mock_admin_auth):
        payload = {"ip": ip, "name": name, "is_active": True}
        resp = client.post("/api/v1/devices", json=payload)

        assert resp.status_code == 422
        assert (
            resp.json()["detail"][0]["msg"]
            == "Value error, Name can only contain letters, numbers, '_' and '-' (up to 15 characters)"
        )

    @pytest.mark.parametrize(
        "ip, name",
        [
            ("192.168.1.20", "a" * 15),
            ("192.168.1.21", "a"),
            ("192.168.1.22", "srv_01-test"),
            ("2001:db8::1", "ipv6-device"),
        ],
    )
    def test_create_device_valid_name(self, client, ip, name, mock_admin_auth):
        resp = client.post("/api/v1/devices", json={"ip": ip, "name": name, "is_active": True})
        assert resp.status_code == 201

        listed = client.get("/api/v1/devices").json()
        assert any(d["name"] == name for d in listed)

    def test_create_device_ip_leading_zeros_rejected(self, client, mock_admin_auth):
        resp = client.post(
            "/api/v1/devices",
            json={"ip": "192.168.001.001", "name": "test", "is_active": True},
        )
        assert resp.status_code == 422

    def test_create_device_ip_cidr_rejected(self, client, mock_admin_auth):
        resp = client.post(
            "/api/v1/devices", json={"ip": "10.0.0.1/24", "name": "test", "is_active": True}
        )
        assert resp.status_code == 422

    def test_create_device_trims_whitespace(self, client, mock_admin_auth):
        resp = client.post(
            "/api/v1/devices",
            json={
                "ip": "  192.168.1.30  ",
                "name": "  trimmed-name  ",
                "is_active": True,
            },
        )
        assert resp.status_code == 201

        listed = client.get("/api/v1/devices").json()
        dev = next(d for d in listed if d["name"] == "trimmed-name")
        assert dev["ip"] == "192.168.1.30"

    def test_create_device_missing_name(self, client, mock_admin_auth):
        resp = client.post("/api/v1/devices", json={"ip": "192.168.1.40", "is_active": True})
        assert resp.status_code == 422
        assert resp.json()["detail"][0]["type"] == "missing"

    def test_create_device_name_wrong_type(self, client, mock_admin_auth):
        resp = client.post(
            "/api/v1/devices", json={"ip": "192.168.1.41", "name": 12345, "is_active": True}
        )
        assert resp.status_code == 422

    def test_create_device_ipv4_mapped_ipv6(self, client, mock_admin_auth):
        resp = client.post(
            "/api/v1/devices",
            json={"ip": "::ffff:192.168.1.1", "name": "mapped-ipv6", "is_active": True},
        )
        assert resp.status_code == 201

        listed = client.get("/api/v1/devices").json()
        dev = next(d for d in listed if d["name"] == "mapped-ipv6")
        assert dev["ip"] == "::ffff:192.168.1.1"
