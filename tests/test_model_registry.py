from sqlalchemy import select

from mona_core import model_registry
from mona_core.db import TrainedModel


def _all_ids(db):
    return set(db.scalars(select(TrainedModel.id)).all())


def _active_ids(db):
    return set(
        db.scalars(
            select(TrainedModel.id).where(TrainedModel.is_active.is_(True))
        ).all()
    )


class TestListModels:
    def test_user_models_newest_first(self, db_session, make_trained_model):
        first = make_trained_model(is_active=False).id
        second = make_trained_model(is_active=False).id
        make_trained_model(trained_by="auto", is_active=False)

        models = model_registry.list_models(db_session)

        assert [m.id for m in models] == [second, first]

    def test_empty(self, db_session):
        assert model_registry.list_models(db_session) == []


class TestGetActive:
    def test_none_when_no_models(self, db_session):
        assert model_registry.get_active(db_session) is None

    def test_none_when_nothing_is_active(self, db_session, make_trained_model):
        make_trained_model(is_active=False)

        assert model_registry.get_active(db_session) is None

    def test_returns_active_model(self, db_session, make_trained_model):
        make_trained_model(is_active=False)
        active = make_trained_model(is_active=True).id

        found = model_registry.get_active(db_session)

        assert found is not None
        assert found.id == active

    def test_ignores_models_not_trained_by_user(self, db_session, make_trained_model):
        make_trained_model(trained_by="auto", is_active=True)

        assert model_registry.get_active(db_session) is None

    def test_newest_wins_if_several_are_active(self, db_session, make_trained_model):
        make_trained_model(is_active=True)
        newest = make_trained_model(is_active=True).id

        found = model_registry.get_active(db_session)

        assert found is not None
        assert found.id == newest


class TestDeactivateAll:
    def test_returns_number_of_deactivated_models(
        self, db_session, make_trained_model
    ):
        make_trained_model(is_active=True)
        make_trained_model(is_active=True)
        make_trained_model(is_active=False)

        count = model_registry.deactivate_all(db_session)

        assert count == 2
        assert _active_ids(db_session) == set()
        assert model_registry.get_active(db_session) is None

    def test_nothing_to_deactivate(self, db_session):
        assert model_registry.deactivate_all(db_session) == 0


class TestActivate:
    def test_activates_model_and_deactivates_the_rest(
        self, db_session, make_trained_model
    ):
        old = make_trained_model(is_active=True).id
        target = make_trained_model(is_active=False).id

        assert model_registry.activate(db_session, target) is True

        assert _active_ids(db_session) == {target}
        assert old not in _active_ids(db_session)

    def test_unknown_id_returns_false_and_keeps_active_model(
        self, db_session, make_trained_model
    ):
        active = make_trained_model(is_active=True).id

        assert model_registry.activate(db_session, 999_999) is False

        assert _active_ids(db_session) == {active}

    def test_model_not_trained_by_user_cannot_be_activated(
        self, db_session, make_trained_model
    ):
        active = make_trained_model(is_active=True).id
        foreign = make_trained_model(trained_by="auto", is_active=False).id

        assert model_registry.activate(db_session, foreign) is False

        assert _active_ids(db_session) == {active}


class TestDeleteOne:
    def test_deletes_inactive_model(self, db_session, make_trained_model):
        model_id = make_trained_model(is_active=False).id

        assert model_registry.delete_one(db_session, model_id) == (True, False)

        assert model_id not in _all_ids(db_session)

    def test_reports_that_deleted_model_was_active(
        self, db_session, make_trained_model
    ):
        model_id = make_trained_model(is_active=True).id

        assert model_registry.delete_one(db_session, model_id) == (True, True)

        assert model_registry.get_active(db_session) is None

    def test_unknown_id(self, db_session):
        assert model_registry.delete_one(db_session, 999_999) == (False, False)

    def test_model_not_trained_by_user_is_not_deleted(
        self, db_session, make_trained_model
    ):
        foreign = make_trained_model(trained_by="auto", is_active=False).id

        assert model_registry.delete_one(db_session, foreign) == (False, False)

        assert foreign in _all_ids(db_session)


class TestPrune:
    def test_keeps_only_the_newest_models(self, db_session, make_trained_model):
        ids = [make_trained_model(is_active=False).id for _ in range(5)]

        deleted = model_registry.prune(db_session, keep=2)

        assert deleted == 3
        assert _all_ids(db_session) == set(ids[-2:])

    def test_never_deletes_the_active_model(self, db_session, make_trained_model):
        oldest_active = make_trained_model(is_active=True).id
        others = [make_trained_model(is_active=False).id for _ in range(4)]

        deleted = model_registry.prune(db_session, keep=2)

        assert deleted == 2
        assert _all_ids(db_session) == {oldest_active, *others[-2:]}

    def test_does_not_touch_models_not_trained_by_user(
        self, db_session, make_trained_model
    ):
        foreign = make_trained_model(trained_by="auto", is_active=False).id
        for _ in range(3):
            make_trained_model(is_active=False)

        model_registry.prune(db_session, keep=1)

        assert foreign in _all_ids(db_session)

    def test_nothing_to_prune(self, db_session, make_trained_model):
        make_trained_model(is_active=False)

        assert model_registry.prune(db_session, keep=10) == 0