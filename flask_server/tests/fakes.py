"""An in-memory stand-in for repository.py, so route tests run without Firestore.

It stores documents with Firestore's camelCase field names and returns them the way the real
repository does ({"id": ..., **fields}), so the real serializers work on its output.
Tests against the Firestore emulator (later) cover repository.py itself.
"""
import copy
import itertools
from datetime import datetime, timedelta, timezone

from google.api_core.exceptions import Conflict

import repository

_START = datetime(2026, 10, 1, tzinfo=timezone.utc)


class FakeRepository:
    def __init__(self):
        self.users = {}
        self.assignments = {}  # {year: {giver: receiver}}
        self.seasons = {}  # {year: {"status", "generation"}}
        self.photos = {}
        self.questions = {}
        self.invites = set()
        self.season_config = None
        self._ids = itertools.count(1)
        self._clock = itertools.count()

    def _now(self):
        # Strictly increasing timestamps, so ordering by createdAt is deterministic
        return _START + timedelta(seconds=next(self._clock))

    @staticmethod
    def _with_id(doc_id, fields):
        return {"id": doc_id, **copy.deepcopy(fields)}

    # Users

    def get_user(self, uid):
        return self._with_id(uid, self.users[uid]) if uid in self.users else None

    def list_users(self):
        return [self._with_id(uid, fields) for uid, fields in self.users.items()]

    def create_user(self, uid, first_name, last_name, email, address):
        if uid in self.users:
            raise repository.AlreadyExists(uid)
        now = self._now()
        self.users[uid] = {
            "firstName": first_name, "lastName": last_name, "email": email, "address": address,
            "profilePicturePath": None, "gifts": [], "createdAt": now, "updatedAt": now,
        }
        return self.get_user(uid)

    def update_user(self, uid, fields):
        if uid not in self.users:
            return None
        self.users[uid].update({repository.USER_FIELDS[name]: value for name, value in fields.items()})
        self.users[uid]["updatedAt"] = self._now()
        return self.get_user(uid)

    def delete_user(self, uid):
        self.users.pop(uid, None)

    def find_user_by_email(self, email):
        return next((self._with_id(uid, f) for uid, f in self.users.items() if f["email"] == email), None)

    def set_gifts(self, uid, gifts):
        if uid not in self.users:
            return None
        self.users[uid]["gifts"] = [{"name": g["name"], "url": g.get("url"), "notes": g.get("notes")} for g in gifts]
        return self.get_user(uid)

    # Config

    def is_invited(self, email):
        return email.lower() in {invited.lower() for invited in self.invites}

    def get_season_config(self):
        return copy.deepcopy(self.season_config)

    # Assignments

    def record_generation(self, year):
        season = self.seasons.setdefault(year, {"generation": 0})
        season["status"] = "matched"
        season["generation"] += 1

    def get_generation(self, year):
        return self.seasons.get(year, {}).get("generation", 0)

    def get_assignment(self, year, giver_uid):
        return self.assignments.get(year, {}).get(giver_uid)

    def list_assignments(self, year):
        return dict(self.assignments.get(year, {}))

    def write_assignments(self, year, mapping):
        existing = self.assignments.setdefault(year, {})
        if any(giver in existing for giver in mapping):
            # The real batch.create() raises AlreadyExists, a Conflict
            raise Conflict("assignment already exists")
        existing.update(mapping)

    def delete_assignment(self, year, giver_uid):
        self.assignments.get(year, {}).pop(giver_uid, None)

    def delete_assignments(self, year):
        self.assignments.pop(year, None)

    # Photos

    def create_photo(self, owner_uid, season, content_type, size_bytes):
        photo_id = f"photo{next(self._ids)}"
        self.photos[photo_id] = {
            "ownerUid": owner_uid, "season": season, "status": "pending",
            "contentType": content_type, "sizeBytes": size_bytes, "createdAt": self._now(),
        }
        return self.get_photo(photo_id)

    def get_photo(self, photo_id):
        return self._with_id(photo_id, self.photos[photo_id]) if photo_id in self.photos else None

    def list_photos(self, season, status="ready"):
        photos = [self._with_id(pid, p) for pid, p in self.photos.items() if p["season"] == season and p["status"] == status]
        return sorted(photos, key=lambda photo: photo["createdAt"], reverse=True)

    def list_photo_seasons(self):
        return sorted({p["season"] for p in self.photos.values() if p["status"] == "ready"}, reverse=True)

    def count_photos(self, owner_uid, season):
        return len([
            p for p in self.photos.values()
            if p["ownerUid"] == owner_uid and p["season"] == season and p["status"] in repository.ACTIVE_PHOTO_STATUSES
        ])

    def list_photos_by_owner(self, owner_uid):
        return [self._with_id(pid, p) for pid, p in self.photos.items() if p["ownerUid"] == owner_uid]

    def count_photos_by_owner(self, season):
        counts = {}
        for p in self.photos.values():
            if p["season"] == season and p["status"] in repository.ACTIVE_PHOTO_STATUSES:
                counts[p["ownerUid"]] = counts.get(p["ownerUid"], 0) + 1
        return counts

    def mark_photo_ready(self, photo_id, display_path, thumb_path):
        self.photos[photo_id].update({
            "status": "ready", "displayPath": display_path, "thumbPath": thumb_path, "processedAt": self._now(),
        })

    def delete_photo(self, photo_id):
        self.photos.pop(photo_id, None)

    # Questions

    def create_question(self, text):
        question_id = f"question{next(self._ids)}"
        self.questions[question_id] = {"text": text, "createdAt": self._now(), "answered": False}
        return self._with_id(question_id, self.questions[question_id])

    def list_questions(self):
        questions = [self._with_id(qid, q) for qid, q in self.questions.items()]
        return sorted(questions, key=lambda question: question["createdAt"], reverse=True)

    # Test helpers (not part of repository.py)

    def add_user(self, uid, first_name, last_name="Tester", email=None, address="1 Elf Rd", **extra):
        self.create_user(uid, first_name, last_name, email or f"{uid}@example.com", address)
        self.users[uid].update(extra)
        return self.get_user(uid)

    def add_ready_photo(self, owner_uid, season):
        photo = self.create_photo(owner_uid, season, "image/jpeg", 1000)
        self.mark_photo_ready(
            photo["id"],
            f"display/{season}/{owner_uid}/{photo['id']}.webp",
            f"thumbs/{season}/{owner_uid}/{photo['id']}.webp",
        )
        return self.get_photo(photo["id"])


def install(monkeypatch, fake):
    """Points every data-access function in repository.py at the fake. Serializers stay real."""
    for name in dir(FakeRepository):
        if not name.startswith("_") and name not in ("add_user", "add_ready_photo") and hasattr(repository, name):
            monkeypatch.setattr(repository, name, getattr(fake, name))
