"""F1 generate_matches and F2 notify_match."""
from datetime import datetime, timedelta, timezone

import pytest

import main
import store
from tests.conftest import firestore_event, pubsub_event

PAST = datetime.now(timezone.utc) - timedelta(minutes=1)
FUTURE = datetime(2026, 11, 25, 17, tzinfo=timezone.utc) + timedelta(days=365 * 10)


def add_users(db, *uids):
    for uid in uids:
        db.put(f"users/{uid}", {"firstName": uid.title(), "email": f"{uid}@example.com", "gifts": []})


def assignments(db, year):
    prefix = f"seasons/{year}/assignments/"
    return {path[len(prefix):]: fields["receiverUid"] for path, fields in db.docs.items() if path.startswith(prefix)}


@pytest.fixture(autouse=True)
def season(db):
    db.put("config/season", {"year": 2026, "revealAt": PAST, "status": "open"})


# F1 generate_matches

def test_draws_one_cycle_and_marks_the_season(db, sent):
    add_users(db, "ann", "bo", "cy", "di")
    main.generate_matches(pubsub_event("generate_matches"))

    drawn = assignments(db, 2026)
    assert set(drawn) == {"ann", "bo", "cy", "di"} and sorted(drawn.values()) == sorted(drawn)
    assert all(giver != receiver for giver, receiver in drawn.items())
    assert db.data("seasons/2026")["status"] == "matched" and db.data("seasons/2026")["generation"] == 1
    assert db.data("config/season")["status"] == "matched"
    assert sent == []


def test_ignores_other_scheduler_actions(db, sent):
    add_users(db, "ann", "bo")
    for action in ("gift_reminder", "close_season", None):
        main.generate_matches(pubsub_event(action))
    assert assignments(db, 2026) == {}


def test_never_redraws_existing_matches(db, sent):
    add_users(db, "ann", "bo", "cy")
    db.put("seasons/2026/assignments/ann", {"receiverUid": "bo"})
    main.generate_matches(pubsub_event("generate_matches"))
    assert assignments(db, 2026) == {"ann": "bo"}


def test_a_redelivered_message_runs_once(db, sent, monkeypatch):
    add_users(db, "ann", "bo", "cy")
    draws = []
    real = main.generate_derangement
    monkeypatch.setattr(main, "generate_derangement", lambda *args: draws.append(1) or real(*args))
    event = pubsub_event("generate_matches", event_id="same-message")
    main.generate_matches(event)
    del db.docs["seasons/2026"]  # even if the season looked untouched
    for path in list(db.docs):
        if path.startswith("seasons/2026/assignments/"):
            del db.docs[path]
    main.generate_matches(event)
    assert len(draws) == 1


def test_avoids_last_years_pairs_only(db, sent):
    add_users(db, "ann", "bo", "cy")
    for giver, receiver in (("ann", "bo"), ("bo", "cy"), ("cy", "ann")):
        db.put(f"seasons/2025/assignments/{giver}", {"receiverUid": receiver})
    # 2024 used the only other cycle; it must still be allowed
    for giver, receiver in (("ann", "cy"), ("cy", "bo"), ("bo", "ann")):
        db.put(f"seasons/2024/assignments/{giver}", {"receiverUid": receiver})
    main.generate_matches(pubsub_event("generate_matches"))
    assert assignments(db, 2026) == {"ann": "cy", "cy": "bo", "bo": "ann"}


def test_when_every_draw_repeats_last_year_it_emails_the_admin(db, sent):
    add_users(db, "ann", "bo")
    db.put("seasons/2025/assignments/ann", {"receiverUid": "bo"})
    db.put("seasons/2025/assignments/bo", {"receiverUid": "ann"})
    main.generate_matches(pubsub_event("generate_matches"))
    assert assignments(db, 2026) == {}
    [(to, subject, body)] = sent
    assert to == ["admin@example.com"] and "couldn't be drawn" in subject and "allow repeats" in body


def test_too_few_people_emails_the_admin(db, sent):
    add_users(db, "ann")
    main.generate_matches(pubsub_event("generate_matches"))
    assert assignments(db, 2026) == {}
    assert "Only 1 member signed up" in sent[0][2]


def test_action_can_come_from_a_message_attribute(db, sent):
    add_users(db, "ann", "bo")
    main.generate_matches(pubsub_event(raw_data="", attributes={"action": "generate_matches"}))
    assert len(assignments(db, 2026)) == 2


@pytest.mark.parametrize("raw", ["!!!not base64", "bm90IGpzb24=", "WzEsMl0="])  # garbage, "not json", "[1,2]"
def test_malformed_messages_are_ignored(db, sent, raw):
    add_users(db, "ann", "bo")
    main.generate_matches(pubsub_event(raw_data=raw))
    assert assignments(db, 2026) == {}


# F2 notify_match

@pytest.fixture
def drawn(db):
    add_users(db, "ann", "bo")
    db.put("seasons/2026", {"status": "matched", "generation": 1})
    db.put("seasons/2026/assignments/ann", {"receiverUid": "bo"})
    return "seasons/2026/assignments/ann"


def test_emails_the_giver_without_naming_their_match(db, sent, drawn):
    main.notify_match(firestore_event(drawn))
    [(to, subject, body)] = sent
    assert to == ["ann@example.com"]
    assert subject == "Your Secret Santa match is ready"
    assert "Hi Ann," in body and "Log in to see who you're getting a gift for" in body
    assert "Bo" not in subject + body and "bo@" not in body
    assert db.data(drawn)["notifiedAt"]


def test_before_the_reveal_the_email_says_when_to_look(db, sent, drawn):
    db.docs["config/season"]["revealAt"] = datetime(2099, 11, 25, 17, tzinfo=timezone.utc)
    main.notify_match(firestore_event(drawn))
    assert "from November 25 at 12pm Eastern" in sent[0][2]


def test_redrawn_matches_say_so(db, sent, drawn):
    db.docs["seasons/2026"]["generation"] = 2
    main.notify_match(firestore_event(drawn))
    assert sent[0][1] == "Your Secret Santa match has changed"
    assert "redrawn" in sent[0][2]


def test_each_assignment_is_emailed_once(db, sent, drawn):
    event = firestore_event(drawn, event_id="same")
    main.notify_match(event)
    main.notify_match(event)  # redelivery of the same event
    main.notify_match(firestore_event(drawn))  # a different event for an already-notified assignment
    assert len(sent) == 1


def test_assignment_deleted_by_a_regenerate_is_skipped(db, sent, drawn):
    del db.docs[drawn]
    main.notify_match(firestore_event(drawn))
    assert sent == []


def test_giver_without_an_email_is_skipped(db, sent, drawn):
    del db.docs["users/ann"]
    main.notify_match(firestore_event(drawn))
    assert sent == []


def test_a_failed_send_can_be_retried(db, drawn, monkeypatch):
    attempts = []

    def flaky_send(to, subject, body):
        attempts.append(to)
        if len(attempts) == 1:
            raise OSError("SMTP unavailable")
    monkeypatch.setattr(main.mailer, "send", flaky_send)
    event = firestore_event(drawn, event_id="retried")

    with pytest.raises(OSError):
        main.notify_match(event)
    assert "notifiedAt" not in db.data(drawn)

    main.notify_match(event)  # the platform retries the same event
    assert len(attempts) == 2 and db.data(drawn)["notifiedAt"]


def test_falls_back_to_that_years_nov_25_for_other_seasons(db, sent):
    add_users(db, "ann", "bo")
    db.docs["config/season"] = {"year": 2025, "revealAt": PAST}
    db.put("seasons/2099/assignments/ann", {"receiverUid": "bo"})
    main.notify_match(firestore_event("seasons/2099/assignments/ann"))
    assert "from November 25 at 12pm Eastern" in sent[0][2]


def test_store_falls_back_to_nov_25_when_config_is_missing(db):
    del db.docs["config/season"]
    year, reveal_at = store.current_season()
    assert reveal_at == datetime(year, 11, 25, 17, tzinfo=timezone.utc)
