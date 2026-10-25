"""repository.py's own logic: serializers, field mapping and error handling.

Firestore is replaced with MagicMock, so these check what the repository asks Firestore to do,
not Firestore's behavior. Queries and indexes need the emulator, which is for integration tests.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from firebase_admin import firestore
from google.api_core.exceptions import AlreadyExists as FirestoreAlreadyExists
from google.api_core.exceptions import NotFound

import repository
from server import create_app


@pytest.fixture
def db():
    app = create_app({"TESTING": True, "ALLOWED_ORIGINS": []})
    app.extensions["firestore"] = MagicMock(name="firestore")
    with app.app_context():
        yield app.extensions["firestore"]


def snapshot(doc_id, fields):
    snap = MagicMock(id=doc_id, exists=fields is not None)
    snap.to_dict.return_value = fields
    snap.get.side_effect = lambda key: fields[key]
    return snap


def user_doc(db):
    return db.collection.return_value.document.return_value


# Serializers

def test_serialize_user_maps_firestore_fields_to_api_names():
    user = {"id": "u1", "firstName": "Ann", "lastName": "Lee", "email": "a@x.com", "address": "1 Rd",
            "gifts": [], "profilePicturePath": "avatars/u1/p.webp", "createdAt": object()}
    assert repository.serialize_user(user, "https://signed") == {
        "id": "u1", "first_name": "Ann", "last_name": "Lee", "email": "a@x.com", "address": "1 Rd",
        "profile_picture_url": "https://signed",
    }


def test_serialize_user_tolerates_missing_last_name_from_old_rows():
    assert repository.serialize_user({"id": "u1", "firstName": "Ann"})["last_name"] is None


def test_serialize_gifts_uses_position_as_id():
    user = {"id": "u1", "gifts": [{"name": "A", "url": "https://a"}, {"name": "B", "notes": "n"}]}
    assert repository.serialize_gifts(user) == [
        {"id": 0, "user_id": "u1", "name": "A", "url": "https://a", "notes": None, "position": 0},
        {"id": 1, "user_id": "u1", "name": "B", "url": None, "notes": "n", "position": 1},
    ]
    assert repository.serialize_gifts({"id": "u1"}) == []


def test_serialize_question_has_no_asker():
    created = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    assert repository.serialize_question({"id": "q", "text": "Hi?", "createdAt": created, "answered": False}) == {
        "id": "q", "text": "Hi?", "created_at": "2026-11-01T12:00:00+00:00", "answered": False,
    }


# Users

def test_get_user_returns_none_when_missing(db):
    user_doc(db).get.return_value = snapshot("u1", None)
    assert repository.get_user("u1") is None


def test_create_user_never_overwrites(db):
    user_doc(db).create.side_effect = FirestoreAlreadyExists("exists")
    with pytest.raises(repository.AlreadyExists):
        repository.create_user("u1", "Ann", "Lee", "a@x.com", "1 Rd")
    user_doc(db).set.assert_not_called()


def test_create_user_starts_with_no_gifts_or_picture(db):
    user_doc(db).get.return_value = snapshot("u1", {"firstName": "Ann"})
    repository.create_user("u1", "Ann", "Lee", "a@x.com", "1 Rd")
    fields = user_doc(db).create.call_args.args[0]
    assert fields["gifts"] == [] and fields["profilePicturePath"] is None
    assert fields["firstName"] == "Ann" and fields["lastName"] == "Lee"


def test_update_user_maps_api_names_and_stamps_updated_at(db):
    user_doc(db).get.return_value = snapshot("u1", {"firstName": "Ann"})
    repository.update_user("u1", {"first_name": "Ann", "profile_picture_path": None})
    assert user_doc(db).update.call_args.args[0] == {
        "firstName": "Ann", "profilePicturePath": None, "updatedAt": firestore.SERVER_TIMESTAMP,
    }


def test_update_user_rejects_unknown_fields(db):
    with pytest.raises(KeyError):
        repository.update_user("u1", {"is_admin": True})


@pytest.mark.parametrize("call", [
    lambda: repository.update_user("u1", {"address": "x"}),
    lambda: repository.set_gifts("u1", []),
])
def test_updates_to_a_missing_user_return_none(db, call):
    user_doc(db).update.side_effect = NotFound("missing")
    assert call() is None


def test_set_gifts_stores_only_known_fields(db):
    user_doc(db).get.return_value = snapshot("u1", {})
    repository.set_gifts("u1", [{"name": "A", "url": None, "notes": "n", "extra": "dropped"}])
    assert user_doc(db).update.call_args.args[0]["gifts"] == [{"name": "A", "url": None, "notes": "n"}]


# Config

@pytest.mark.parametrize("fields, expected", [
    (None, False), ({}, False), ({"emails": ["Ann@Example.com"]}, True), ({"emails": ["bo@x.com"]}, False),
])
def test_is_invited(db, fields, expected):
    user_doc(db).get.return_value = snapshot("invites", fields)
    assert repository.is_invited("ann@example.com") is expected


@pytest.mark.parametrize("fields, expected", [(None, 0), ({"status": "open"}, 0), ({"generation": 3}, 3)])
def test_get_generation(db, fields, expected):
    db.collection.return_value.document.return_value.get.return_value = snapshot("2026", fields)
    assert repository.get_generation(2026) == expected


# Assignments

def test_write_assignments_creates_in_one_batch_and_never_overwrites(db):
    batch = db.batch.return_value
    repository.write_assignments(2026, {"a": "b", "b": "a"})
    assert batch.create.call_count == 2 and batch.set.call_count == 0
    assert [call.args[1]["receiverUid"] for call in batch.create.call_args_list] == ["b", "a"]
    batch.commit.assert_called_once()


def test_record_generation_increments_atomically(db):
    repository.record_generation(2026)
    season = db.collection.return_value.document.return_value
    fields, = season.set.call_args.args
    assert fields["status"] == "matched"
    assert isinstance(fields["generation"], firestore.Increment)
    assert season.set.call_args.kwargs == {"merge": True}


# Photos and questions

def test_create_photo_starts_pending(db):
    photos = db.collection.return_value
    photos.document.return_value.id = "p1"
    photos.document.return_value.get.return_value = snapshot("p1", {"status": "pending"})
    repository.create_photo("u1", 2026, "image/jpeg", 10)
    fields = photos.document.return_value.set.call_args.args[0]
    assert fields["status"] == "pending" and fields["ownerUid"] == "u1" and fields["season"] == 2026


def test_create_question_stores_only_text_date_and_answered(db):
    ref = MagicMock()
    ref.get.return_value = snapshot("q1", {"text": "Hi"})
    db.collection.return_value.add.return_value = (None, ref)
    repository.create_question("Hi")
    assert set(db.collection.return_value.add.call_args.args[0]) == {"text", "createdAt", "answered"}


def test_list_photos_sorts_newest_first(db):
    early, late = datetime(2026, 11, 1, tzinfo=timezone.utc), datetime(2026, 11, 2, tzinfo=timezone.utc)
    query = db.collection.return_value.where.return_value.where.return_value
    query.stream.return_value = [snapshot("old", {"createdAt": early}), snapshot("new", {"createdAt": late})]
    assert [photo["id"] for photo in repository.list_photos(2026)] == ["new", "old"]
