import base64
import io
import itertools
import json

import pytest
from cloudevents.http import CloudEvent
from PIL import Image

import mailer
import store
from tests.fakes import FakeBucket, FakeFirestore

_event_ids = itertools.count(1)


@pytest.fixture
def db(monkeypatch):
    fake = FakeFirestore()
    monkeypatch.setattr(store, "db", lambda: fake)
    return fake


@pytest.fixture
def buckets(monkeypatch):
    created = {}

    def bucket(name):
        return created.setdefault(name, FakeBucket(name))
    monkeypatch.setattr(store, "bucket", bucket)
    return bucket


@pytest.fixture
def sent(monkeypatch):
    """Emails the functions sent, as (to, subject, body)."""
    outbox = []
    monkeypatch.setattr(mailer, "send", lambda to, subject, body: outbox.append((to, subject, body)))
    return outbox


@pytest.fixture(autouse=True)
def admins(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")


def pubsub_event(action=None, event_id=None, attributes=None, raw_data=None):
    data = raw_data if raw_data is not None else base64.b64encode(json.dumps({"action": action}).encode()).decode()
    return CloudEvent(
        {"type": "google.cloud.pubsub.topic.v1.messagePublished", "source": "//pubsub/season-events",
         "id": event_id or f"event-{next(_event_ids)}"},
        {"message": {"data": data, "attributes": attributes or {}}},
    )


def firestore_event(document_path, event_id=None):
    return CloudEvent(
        {"type": "google.cloud.firestore.document.v1.created", "source": "//firestore",
         "id": event_id or f"event-{next(_event_ids)}", "subject": f"documents/{document_path}"},
        None,
    )


def storage_event(bucket, name):
    return CloudEvent(
        {"type": "google.cloud.storage.object.v1.finalized", "source": f"//storage/{bucket}", "id": f"event-{next(_event_ids)}"},
        {"bucket": bucket, "name": name},
    )


def image_bytes(size=(800, 600), mode="RGB", format="JPEG", color=(200, 30, 30), **save_options):
    image = Image.new(mode, size, color if mode != "RGBA" else (*color, 128))
    buffer = io.BytesIO()
    image.save(buffer, format, **save_options)
    return buffer.getvalue()
