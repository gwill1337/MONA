from sqlalchemy.orm import Session

from mona_core.db import TrainedModel

class TestModel:
    def test_model_info_no_model(self, client, mock_user_auth):
        resp = client.get("/api/v1/model-info")
        assert resp.status_code == 200
        assert resp.json() == {
            "status": "no_model",
            "message": "No active model. Using auto-mode.",
        }

    def test_model_info_with_model(self, client, make_trained_model, mock_user_auth):
        make_trained_model(
            model_data=b"binary-blob",
            points_count=1000,
            note="nightly training",
        )

        resp = client.get("/api/v1/model-info")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["model"]["points_count"] == 1000
        assert body["model"]["note"] == "nightly training"

    def test_model_info_ignores_inactive(self, client, make_trained_model, mock_user_auth):
        make_trained_model(is_active=False)

        resp = client.get("/api/v1/model-info")
        assert resp.json()["status"] == "no_model"

    def test_model_info_returns_only_active(self, client, make_trained_model, mock_user_auth):
        make_trained_model(points_count=1, is_active=False, note="old")
        make_trained_model(points_count=2, is_active=True, note="current")

        body = client.get("/api/v1/model-info").json()

        assert body["status"] == "ok"
        assert body["model"]["note"] == "current"
        assert body["model"]["points_count"] == 2

    def test_delete_model(self, client, make_trained_model, mock_admin_auth):
        make_trained_model()

        resp = client.delete("/api/v1/model")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["deleted"] == 1

        assert client.get("/api/v1/model-info").json()["status"] == "no_model"

    def test_delete_model_when_none_exists(self, client, mock_admin_auth):
        resp = client.delete("/api/v1/model")
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 0

class TestModelRegistry:

    def test_list_models_empty(self, client, mock_user_auth):
        resp = client.get("/api/v1/models")

        assert resp.status_code == 200
        assert resp.json() == {"items": []}

    def test_list_models_newest_first(self, client, make_trained_model, mock_user_auth):
        make_trained_model(note="first", is_active=False)
        make_trained_model(note="second", is_active=False)
        make_trained_model(note="third", is_active=True)

        items = client.get("/api/v1/models").json()["items"]

        assert [m["note"] for m in items] == ["third", "second", "first"]

    def test_deactivate_models(self, client, db_session, make_trained_model, mock_admin_auth):
        rec = make_trained_model(is_active=True)

        resp = client.post("/api/v1/models/deactivate")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "Switched to auto-mode."}

        db_session.refresh(rec)
        assert rec.is_active is False
        assert client.get("/api/v1/model-info").json()["status"] == "no_model"
        # сама модель не удалена
        assert len(client.get("/api/v1/models").json()["items"]) == 1

    def test_deactivate_models_when_none_exist(self, client, mock_admin_auth):
        resp = client.post("/api/v1/models/deactivate")

        assert resp.status_code == 200

    def test_deactivate_models_forbidden_for_user(self, client, db_session, make_trained_model, mock_user_auth):
        rec = make_trained_model(is_active=True)

        resp = client.post("/api/v1/models/deactivate")

        assert resp.status_code == 403
        db_session.refresh(rec)
        assert rec.is_active is True

    def test_activate_model(self, client, db_session, make_trained_model, mock_admin_auth):
        old = make_trained_model(note="old", is_active=True)
        new = make_trained_model(note="new", is_active=False)

        resp = client.post(f"/api/v1/models/{new.id}/activate")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "Model activated."}

        db_session.refresh(old)
        db_session.refresh(new)
        assert new.is_active is True
        assert old.is_active is False

        body = client.get("/api/v1/model-info").json()
        assert body["status"] == "ok"
        assert body["model"]["note"] == "new"

    def test_activate_already_active_model(self, client, db_session, make_trained_model, mock_admin_auth):
        rec = make_trained_model(is_active=True)

        resp = client.post(f"/api/v1/models/{rec.id}/activate")

        assert resp.status_code == 200
        db_session.refresh(rec)
        assert rec.is_active is True

    def test_activate_model_not_found(self, client, mock_admin_auth):
        resp = client.post("/api/v1/models/99999/activate")

        assert resp.status_code == 404
        assert resp.json()["message"] == "Model not found"

    def test_activate_model_not_found_keeps_current_active(
        self, client, db_session, make_trained_model, mock_admin_auth
    ):
        rec = make_trained_model(is_active=True)

        client.post("/api/v1/models/99999/activate")

        db_session.refresh(rec)
        assert rec.is_active is True

    def test_activate_model_invalid_id(self, client, mock_admin_auth):
        resp = client.post("/api/v1/models/abc/activate")

        assert resp.status_code == 422

    def test_activate_model_forbidden_for_user(self, client, make_trained_model, mock_user_auth):
        rec = make_trained_model(is_active=False)

        resp = client.post(f"/api/v1/models/{rec.id}/activate")

        assert resp.status_code == 403

    def test_activate_model_commit_error(
        self, client, db_session, make_trained_model, mock_admin_auth, monkeypatch
    ):
        old = make_trained_model(is_active=True)
        new = make_trained_model(is_active=False)

        def broken_commit(self, *args, **kwargs):
            raise RuntimeError("db is down")

        monkeypatch.setattr(Session, "commit", broken_commit)

        resp = client.post(f"/api/v1/models/{new.id}/activate")

        assert resp.status_code == 500
        assert resp.json()["message"] == "Server error"

        db_session.refresh(old)
        db_session.refresh(new)
        assert old.is_active is True
        assert new.is_active is False

    def test_delete_one_model_inactive(self, client, make_trained_model, mock_admin_auth):
        active = make_trained_model(note="active", is_active=True)
        inactive = make_trained_model(note="inactive", is_active=False)

        resp = client.delete(f"/api/v1/models/{inactive.id}")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "deleted": 1, "message": "Model deleted."}

        body = client.get("/api/v1/model-info").json()
        assert body["status"] == "ok"
        assert body["model"]["note"] == "active"
        assert len(client.get("/api/v1/models").json()["items"]) == 1

    def test_delete_one_model_active_falls_back_to_auto(self, client, make_trained_model, mock_admin_auth):
        active = make_trained_model(is_active=True)

        resp = client.delete(f"/api/v1/models/{active.id}")

        assert resp.status_code == 200
        assert resp.json() == {
            "status": "ok",
            "deleted": 1,
            "message": "Model deleted. Switched to auto-mode.",
        }
        assert client.get("/api/v1/model-info").json()["status"] == "no_model"

    def test_delete_one_model_not_found(self, client, mock_admin_auth):
        resp = client.delete("/api/v1/models/99999")

        assert resp.status_code == 404
        assert resp.json()["message"] == "Model not found"

    def test_delete_one_model_forbidden_for_user(self, client, make_trained_model, mock_user_auth):
        rec = make_trained_model()

        resp = client.delete(f"/api/v1/models/{rec.id}")

        assert resp.status_code == 403
        assert len(client.get("/api/v1/models").json()["items"]) == 1

    def test_delete_one_model_commit_error(
        self, client, make_trained_model, mock_admin_auth, monkeypatch
    ):
        rec = make_trained_model()

        def broken_commit(self, *args, **kwargs):
            raise RuntimeError("db is down")

        monkeypatch.setattr(Session, "commit", broken_commit)

        resp = client.delete(f"/api/v1/models/{rec.id}")

        assert resp.status_code == 500
        assert resp.json()["message"] == "Server error"


    def test_delete_all_models_removes_only_user_trained(
        self, client, db_session, make_trained_model, mock_admin_auth
    ):
        make_trained_model(trained_by="user", note="u1", is_active=False)
        make_trained_model(trained_by="user", note="u2", is_active=True)
        make_trained_model(trained_by="auto", note="auto", is_active=False)

        resp = client.delete("/api/v1/model")

        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] == 2
        assert body["message"] == "Models deleted. Celery switched to auto-mode."

        db_session.expire_all()
        remaining = db_session.query(TrainedModel).all()
        assert [m.note for m in remaining] == ["auto"]