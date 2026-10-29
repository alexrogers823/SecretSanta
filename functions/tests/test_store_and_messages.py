"""store.py client setup, and the email wording in messages.py."""
from datetime import datetime, timezone

import main
import messages
import store
from shared import matching


# store.db() / store.bucket(): created once, for this project and its named database

def test_db_initializes_firebase_once_with_the_named_database(monkeypatch):
    calls = []
    apps = []
    monkeypatch.setattr(store, "_db", None)

    def get_app():
        if not apps:
            raise ValueError("no app")
    monkeypatch.setattr(store.firebase_admin, "get_app", get_app)
    monkeypatch.setattr(store.firebase_admin, "initialize_app",
                        lambda options: apps.append(options) or calls.append(("init", options)))
    monkeypatch.setattr(store.firestore, "client", lambda database_id: calls.append(("client", database_id)) or "client")

    assert store.db() == "client"
    assert store.db() == "client"
    assert calls == [("init", {"projectId": "secret-santa-511801"}), ("client", "secret-santa-database")]


def test_db_reuses_an_existing_firebase_app(monkeypatch):
    monkeypatch.setattr(store, "_db", None)
    monkeypatch.setattr(store.firebase_admin, "get_app", lambda: "existing")
    monkeypatch.setattr(store.firebase_admin, "initialize_app", lambda **kwargs: (_ for _ in ()).throw(AssertionError("re-initialized")))
    monkeypatch.setattr(store.firestore, "client", lambda database_id: database_id)
    assert store.db() == "secret-santa-database"


def test_bucket_shares_one_storage_client(monkeypatch):
    clients = []

    class FakeClient:
        def __init__(self, project):
            clients.append(project)

        def bucket(self, name):
            return f"bucket:{name}"
    monkeypatch.setattr(store, "_storage", None)
    monkeypatch.setattr(store.storage, "Client", FakeClient)
    assert store.bucket("secret-santa-photos") == "bucket:secret-santa-photos"
    assert store.bucket("secret-santa-profile-photos") == "bucket:secret-santa-profile-photos"
    assert clients == ["secret-santa-511801"]


# Step 3: the functions use the same matching code as the API

def test_functions_use_the_shared_matching_code():
    assert main.generate_derangement is matching.generate_derangement
    assert main.NoValidMatchError is matching.NoValidMatchError


# messages.py

NOON_EST = datetime(2026, 11, 25, 17, tzinfo=timezone.utc)


def test_reveal_time_is_written_in_eastern_time():
    _, body = messages.match_ready("Ann", redrawn=False, revealed=False, reveal_at=NOON_EST)
    assert "November 25 at 12pm Eastern" in body
    _, body = messages.match_ready("Ann", redrawn=False, revealed=False, reveal_at=NOON_EST.replace(minute=30))
    assert "November 25 at 12:30pm Eastern" in body
    _, body = messages.gift_reminder("Ann", datetime(2026, 11, 25, 14, 5, tzinfo=timezone.utc))
    assert "November 25 at 9:05am Eastern" in body


def test_emails_without_a_first_name_still_greet():
    assert messages.match_ready(None, redrawn=False, revealed=True, reveal_at=NOON_EST)[1].startswith("Hi,\n")
    assert messages.gift_reminder("", NOON_EST)[1].startswith("Hi,\n")


def test_every_email_links_to_the_site():
    bodies = [
        messages.match_ready("Ann", redrawn=True, revealed=True, reveal_at=NOON_EST)[1],
        messages.new_question("Q?")[1],
        messages.gift_reminder("Ann", NOON_EST)[1],
        messages.no_valid_draw(2026)[1],
        messages.not_enough_people(2026, 0)[1],
    ]
    assert all(messages.SITE_URL in body for body in bodies)


def test_admin_emails_point_at_the_admin_page_and_pluralize():
    assert f"{messages.SITE_URL}/admin" in messages.no_valid_draw(2026)[1]
    assert "Only 0 members signed up" in messages.not_enough_people(2026, 0)[1]
    assert "Only 1 member signed up" in messages.not_enough_people(2026, 1)[1]
