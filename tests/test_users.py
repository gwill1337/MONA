from sqlalchemy import select

from mona_core.db import Users

class TestUser:
    # ─── GET /api/v1/users ──────────────────────────────────────────────
    def test_get_users_requires_auth(self, client):
        resp = client.get("/api/v1/users")
        assert resp.status_code == 401
 
    def test_get_users_forbidden_for_regular_user(self, client, mock_user_auth):
        resp = client.get("/api/v1/users")
        assert resp.status_code == 403
 
    def test_get_users_empty_list(self, client, mock_admin_auth):
        resp = client.get("/api/v1/users")
        assert resp.status_code == 200
        assert resp.json() == []
 
    def test_get_users_returns_created_users(self, client, mock_admin_auth, make_user):
        make_user(username="alice", role="user")
        make_user(username="bob", role="admin")
 
        resp = client.get("/api/v1/users")
        assert resp.status_code == 200
 
        body = resp.json()
        assert {u["username"] for u in body} == {"alice", "bob"}
        for u in body:
            # response_model=UserGetOut must never leak the password hash
            assert "password" not in u
            assert "password_hash" not in u
 
    def test_get_users_pagination(self, client, mock_admin_auth, make_user):
        for i in range(5):
            make_user(username=f"user{i}", role="user")
 
        resp = client.get("/api/v1/users", params={"limit": 2, "offset": 0})
        assert resp.status_code == 200
        assert len(resp.json()) == 2
 
        resp2 = client.get("/api/v1/users", params={"limit": 2, "offset": 4})
        assert resp2.status_code == 200
        assert len(resp2.json()) == 1
 
    # ─── POST /api/v1/user ──────────────────────────────────────────────
    def test_create_user_requires_admin(self, client, mock_user_auth):
        resp = client.post(
            "/api/v1/user",
            json={"username": "new_user", "password": "pass1234", "role": "user"},
        )
        assert resp.status_code == 403
 
    def test_create_user_success(self, client, mock_admin_auth, db_session):
        resp = client.post(
            "/api/v1/user",
            json={"username": "newadmin", "password": "supersecret", "role": "admin"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "User created"}
 
        user = db_session.execute(
            select(Users).where(Users.username == "newadmin")
        ).scalar_one()
        assert user.role == "admin"
        assert user.password_hash != "supersecret"
        assert user.check_password("supersecret")
 
    def test_create_user_duplicate_username(self, client, mock_admin_auth, make_user):
        make_user(username="dup", role="user")
 
        resp = client.post(
            "/api/v1/user",
            json={"username": "dup", "password": "whatever1", "role": "user"},
        )
        assert resp.status_code == 409
        assert resp.json()["message"] == "User already exists"
 
    def test_create_user_invalid_role_rejected(self, client, mock_admin_auth):
        resp = client.post(
            "/api/v1/user",
            json={"username": "weird", "password": "whatever1", "role": "superadmin"},
        )
        assert resp.status_code == 422
 
    # ─── DELETE /api/v1/user/{user_id} ─────────────────────────────────
    def test_delete_user_requires_admin(self, client, mock_user_auth, make_user):
        user = make_user(username="victim", role="user")
        resp = client.delete(f"/api/v1/user/{user.id}")
        assert resp.status_code == 403
 
    def test_delete_user_not_found(self, client, mock_admin_auth, make_user):
        # Two admins present so the "last admin" guard doesn't shadow the 404.
        make_user(username="admin1", role="admin")
        make_user(username="admin2", role="admin")
 
        resp = client.delete("/api/v1/user/999999")
        assert resp.status_code == 404
        assert resp.json()["message"] == "User not found"
 
    def test_delete_last_remaining_admin_forbidden(self, client, mock_admin_auth, make_user):
        admin = make_user(username="lonely_admin", role="admin")
 
        resp = client.delete(f"/api/v1/user/{admin.id}")
        assert resp.status_code == 400
        assert resp.json()["message"] == "Cannot delete the last remaining admin"
 
    def test_delete_user_success(self, client, mock_admin_auth, make_user, db_session, mock_redis):
        make_user(username="admin1", role="admin")
        victim = make_user(username="victim", role="user")
 
        resp = client.delete(f"/api/v1/user/{victim.id}")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "User deleted"}
 
        remaining = db_session.execute(
            select(Users).where(Users.id == victim.id)
        ).scalar_one_or_none()
        assert remaining is None
 
    # ─── PATCH /api/v1/user/change-password ────────────────────────────
    def test_change_password_requires_admin(self, client, mock_user_auth, make_user):
        make_user(username="alice", password="oldpass1")
 
        resp = client.patch(
            "/api/v1/user/change-password",
            json={"username": "alice", "new_password": "newpass1"},
        )
        assert resp.status_code == 403
 
    def test_change_password_user_not_found(self, client, mock_admin_auth):
        resp = client.patch(
            "/api/v1/user/change-password",
            json={"username": "ghost", "new_password": "newpass1"},
        )
        assert resp.status_code == 404
        assert resp.json()["message"] == "Username or Password invalid"
 
    def test_change_password_success(self, client, mock_admin_auth, make_user, db_session):
        make_user(username="alice", password="oldpass1")
 
        resp = client.patch(
            "/api/v1/user/change-password",
            json={"username": "alice", "new_password": "brandnewpass"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "Password changed"}
 
        user = db_session.execute(
            select(Users).where(Users.username == "alice")
        ).scalar_one()
        assert user.check_password("brandnewpass")
        assert not user.check_password("oldpass1")
 
    # ─── PATCH /api/v1/user/{user_id}/role ─────────────────────────────
    def test_change_role_requires_admin(self, client, mock_user_auth, make_user):
        target = make_user(username="alice", role="user")
        resp = client.patch(f"/api/v1/user/{target.id}/role", json={"role": "admin"})
        assert resp.status_code == 403
 
    def test_change_role_target_not_found(self, client, mock_admin_auth):
        resp = client.patch("/api/v1/user/999999/role", json={"role": "admin"})
        assert resp.status_code == 404
        assert resp.json()["message"] == "User not found"
 
    def test_change_role_unchanged_is_noop(self, client, mock_admin_auth, make_user):
        target = make_user(username="alice", role="user")
        resp = client.patch(f"/api/v1/user/{target.id}/role", json={"role": "user"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "Role unchanged"}
 
    def test_change_role_promote_to_admin(self, client, mock_admin_auth, make_user, db_session):
        target = make_user(username="alice", role="user")
 
        resp = client.patch(f"/api/v1/user/{target.id}/role", json={"role": "admin"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "Role switched"}
 
        db_session.refresh(target)
        assert target.role == "admin"
 
    def test_change_role_demote_last_admin_forbidden(self, client, mock_admin_auth, make_user):
        target = make_user(username="only_admin", role="admin")
 
        resp = client.patch(f"/api/v1/user/{target.id}/role", json={"role": "user"})
        assert resp.status_code == 400
        assert resp.json()["message"] == "Cannot demote the last remaining admin"
 
    def test_change_role_demote_when_multiple_admins_exist(
        self, client, mock_admin_auth, make_user, db_session
    ):
        make_user(username="admin1", role="admin")
        target = make_user(username="admin2", role="admin")
 
        resp = client.patch(f"/api/v1/user/{target.id}/role", json={"role": "user"})
        assert resp.status_code == 200
 
        db_session.refresh(target)
        assert target.role == "user"
 
    def test_change_role_cannot_change_own_role(self, client, mock_admin_auth, make_user):
        # The endpoint's own-account guard only fires on the "user -> admin"
        # branch (see the if/elif chain in change_user_role): it compares the
        # target row's username against the authenticated session's username.
        target = make_user(username=mock_admin_auth.username, role="user")
 
        resp = client.patch(f"/api/v1/user/{target.id}/role", json={"role": "admin"})
        assert resp.status_code == 403
        assert resp.json()["message"] == "You cannot change your own role"