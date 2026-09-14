from datetime import UTC, datetime

from mona_core.db import TrainedModel

class TestModel:
    def test_model_info_no_model(self, client, mock_user_auth):
        resp = client.get("/api/v1/model-info")
        assert resp.status_code == 200
        assert resp.json() == {
            "status": "no_model",
            "message": "Model is not manually trained yet. Using auto-mode.",
        }

    def test_model_info_with_model(self, client, db_session, mock_user_auth):
        db_session.add(
            TrainedModel(
                model_data=b"binary-blob",
                trained_by="user",
                points_count=1000,
                period_from=datetime(2026, 1, 1, tzinfo=UTC),
                period_to=datetime(2026, 1, 2, tzinfo=UTC),
                note="nightly training",
            )
        )
        db_session.commit()

        resp = client.get("/api/v1/model-info")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["model"]["points_count"] == 1000
        assert body["model"]["note"] == "nightly training"

    def test_model_info_ignores_non_user_trained(
        self, client, db_session, mock_user_auth
    ):
        db_session.add(
            TrainedModel(
                model_data=b"x",
                trained_by="auto",
                points_count=1,
                period_from=datetime(2026, 1, 1, tzinfo=UTC),
                period_to=datetime(2026, 1, 2, tzinfo=UTC),
                note="",
            )
        )
        db_session.commit()

        resp = client.get("/api/v1/model-info")
        assert resp.json()["status"] == "no_model"

    def test_delete_model(self, client, db_session, mock_admin_auth):
        db_session.add(
            TrainedModel(
                model_data=b"x",
                trained_by="user",
                points_count=1,
                period_from=datetime(2026, 1, 1, tzinfo=UTC),
                period_to=datetime(2026, 1, 2, tzinfo=UTC),
                note="",
            )
        )
        db_session.commit()

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