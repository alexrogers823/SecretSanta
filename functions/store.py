"""Firestore and Cloud Storage access shared by every function."""
import os
from datetime import datetime, timedelta, timezone

import firebase_admin
from firebase_admin import firestore
from google.api_core.exceptions import Conflict
from google.cloud import storage

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "secret-santa-511801")
DATABASE = os.environ.get("FIRESTORE_DATABASE", "secret-santa-database")

# Nov 25 is always after daylight saving ends, so Eastern time is a fixed UTC-5 that day
EASTERN_STANDARD_TIME = timezone(timedelta(hours=-5))
# How long a "this event was handled" marker is kept (a Firestore TTL policy on expireAt can clean them up)
EVENT_MARKER_DAYS = 30

_db = None
_storage = None


def db():
    global _db
    if _db is None:
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(options={"projectId": PROJECT})
        _db = firestore.client(database_id=DATABASE)
    return _db


def bucket(name):
    global _storage
    if _storage is None:
        _storage = storage.Client(project=PROJECT)
    return _storage.bucket(name)


def now():
    return datetime.now(timezone.utc)


def current_season():
    """Returns (year, reveal_at) from config/season, falling back to this year and Nov 25 at 12pm Eastern,
    the same rule as the API (flask_server/season.py)."""
    snapshot = db().collection("config").document("season").get()
    config = (snapshot.to_dict() if snapshot.exists else None) or {}
    year = config.get("year") or datetime.now(EASTERN_STANDARD_TIME).year
    reveal_at = config.get("revealAt") or datetime(year, 11, 25, 12, tzinfo=EASTERN_STANDARD_TIME)
    return year, reveal_at


def run_once(key, task):
    """Runs task() only the first time it's called with this key, so a redelivered event does nothing.

    Pub/Sub, Eventarc and Cloud Storage all deliver events at least once. The claim is a document
    created atomically; if the task fails, the claim is released so a retry can run it again.
    """
    marker = db().collection("functionEvents").document(key.replace("/", "_"))
    try:
        marker.create({"claimedAt": firestore.SERVER_TIMESTAMP, "expireAt": now() + timedelta(days=EVENT_MARKER_DAYS)})
    except Conflict:
        return False
    try:
        task()
    except Exception:
        marker.delete()
        raise
    return True
