"""F3 notify_admin_question, F4 gift_reminder (with F5 close_season), the mailer and run_once."""
import inspect
import re
from datetime import datetime, timedelta, timezone

import pytest

import mailer
import main
import store
from tests.conftest import firestore_event, pubsub_event

FUTURE = datetime(2099, 11, 25, 17, tzinfo=timezone.utc)


# F3 notify_admin_question

@pytest.fixture
def question(db):
    db.put("questions/q1", {"text": "Is there a price limit?", "createdAt": datetime.now(timezone.utc), "answered": False})
    return "questions/q1"


def test_emails_the_admins_the_question_text(db, sent, question, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com, second@example.com")
    main.notify_admin_question(firestore_event(question))
    [(to, subject, body)] = sent
    assert to == ["admin@example.com", "second@example.com"]
    assert subject == "New anonymous Secret Santa question"
    assert "Is there a price limit?" in body and "/admin" in body
    assert db.data(question)["notifiedAt"]


def test_question_emails_have_no_way_to_name_the_asker():
    # The handler only ever reads the question's text
    source = inspect.getsource(main._notify_admin_question)
    assert "askerUid" not in source and "users" not in source
    assert not re.search(r"logger\.\w+\(.*text", source)


def test_each_question_is_emailed_once(db, sent, question):
    event = firestore_event(question, event_id="same")
    main.notify_admin_question(event)
    main.notify_admin_question(event)
    main.notify_admin_question(firestore_event(question))
    assert len(sent) == 1


def test_without_admin_emails_nothing_is_sent(db, sent, question, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "")
    main.notify_admin_question(firestore_event(question))
    assert sent == [] and "notifiedAt" not in db.data(question)


def test_a_missing_question_is_skipped(db, sent):
    main.notify_admin_question(firestore_event("questions/gone"))
    assert sent == []


# F4 gift_reminder and F5 close_season

@pytest.fixture
def members(db):
    db.put("config/season", {"year": 2026, "revealAt": FUTURE})
    db.put("users/ann", {"firstName": "Ann", "email": "ann@example.com", "gifts": []})
    db.put("users/bo", {"firstName": "Bo", "email": "bo@example.com", "gifts": [{"name": "Socks"}]})
    db.put("users/cy", {"firstName": "Cy", "email": "cy@example.com"})  # no gifts field at all
    db.put("users/old", {"firstName": "Old", "gifts": []})  # no email


def test_reminds_only_members_without_gifts_one_email_each(db, sent, members):
    main.gift_reminder(pubsub_event("gift_reminder"))
    assert sorted(to for to, _, _ in sent) == [["ann@example.com"], ["cy@example.com"]]
    body = dict((to[0], body) for to, _, body in sent)["ann@example.com"]
    assert "Hi Ann," in body and "November 25 at 12pm Eastern" in body


def test_no_reminders_after_the_reveal(db, sent, members):
    db.docs["config/season"]["revealAt"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    main.gift_reminder(pubsub_event("gift_reminder"))
    assert sent == []


def test_a_redelivered_reminder_emails_nobody_twice(db, sent, members):
    event = pubsub_event("gift_reminder", event_id="same")
    main.gift_reminder(event)
    main.gift_reminder(event)
    assert len(sent) == 2


def test_one_failed_reminder_does_not_stop_the_others_and_can_be_retried(db, members, monkeypatch):
    delivered = []
    ann_attempts = []

    def send(to, subject, body):
        if to == ["ann@example.com"]:
            ann_attempts.append(1)
            if len(ann_attempts) == 1:  # only Ann's first attempt fails
                delivered.append(("ann-failed", None))
                raise OSError("SMTP hiccup")
        delivered.append((to[0].split("@")[0], subject))
    monkeypatch.setattr(main.mailer, "send", send)
    event = pubsub_event("gift_reminder", event_id="retry-me")

    with pytest.raises(RuntimeError, match="1 gift reminder"):
        main.gift_reminder(event)
    assert ("cy", "Add your Secret Santa wish list") in delivered

    main.gift_reminder(event)  # retry: only Ann is emailed again
    assert [who for who, _ in delivered] == ["ann-failed", "cy", "ann"]


def test_close_season_marks_the_season_closed(db, sent, members):
    main.gift_reminder(pubsub_event("close_season"))
    assert db.data("config/season")["status"] == "closed"
    assert db.data("config/season")["year"] == 2026
    assert sent == []


def test_gift_reminder_ignores_the_generate_matches_message(db, sent, members):
    main.gift_reminder(pubsub_event("generate_matches"))
    assert sent == [] and "status" not in db.data("config/season")


# run_once

def test_run_once_runs_a_key_once_and_releases_it_on_failure(db):
    calls = []
    assert store.run_once("k", lambda: calls.append(1)) is True
    assert store.run_once("k", lambda: calls.append(2)) is False
    assert calls == [1]

    with pytest.raises(ValueError):
        store.run_once("k2", lambda: (_ for _ in ()).throw(ValueError("boom")))
    assert store.run_once("k2", lambda: calls.append(3)) is True
    assert calls == [1, 3]


def test_run_once_markers_expire(db):
    store.run_once("seasons/2026/x", lambda: None)
    [(path, marker)] = [(p, d) for p, d in db.docs.items() if p.startswith("functionEvents/")]
    assert path == "functionEvents/seasons_2026_x"  # slashes can't appear in a document id
    assert marker["expireAt"] - datetime.now(timezone.utc) > timedelta(days=29)


# mailer

class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.calls = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, message):
        self.calls.append(("send", message))


def test_mailer_sends_over_starttls_on_587(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "santa@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    FakeSMTP.instances.clear()

    mailer.send(["ann@example.com", "bo@example.com"], "Subject", "Body text")

    [smtp] = FakeSMTP.instances
    assert (smtp.host, smtp.port) == ("smtp.gmail.com", 587)
    assert smtp.calls[0] == "starttls"  # encrypted before the password is sent
    assert smtp.calls[1] == ("login", "santa@gmail.com", "app-password")
    message = smtp.calls[2][1]
    assert message["From"] == "Secret Santa <santa@gmail.com>"
    assert message["To"] == "ann@example.com, bo@example.com"
    assert message["Subject"] == "Subject" and message.get_content().strip() == "Body text"


def test_mailer_explains_missing_configuration(monkeypatch):
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    with pytest.raises(mailer.MailerNotConfigured, match="smtp-password"):
        mailer.send(["a@example.com"], "s", "b")


def test_mailer_module_does_not_shadow_the_standard_library():
    import email.message
    assert email.message.__file__ != mailer.__file__
