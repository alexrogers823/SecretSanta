from firebase_admin import firestore
from flask import current_app
from google.api_core.exceptions import Conflict, NotFound

# Firestore stores camelCase fields; the API keeps the snake_case names the client already uses
USER_FIELDS = {
    "first_name": "firstName",
    "last_name": "lastName",
    "email": "email",
    "address": "address",
    "profile_picture_path": "profilePicturePath",
}

ACTIVE_PHOTO_STATUSES = ["pending", "ready"]


class AlreadyExists(Exception):
    pass


def _db():
    return current_app.extensions["firestore"]


def _with_id(snapshot):
    if not snapshot.exists:
        return None
    return {"id": snapshot.id, **snapshot.to_dict()}


# Users

def get_user(uid):
    return _with_id(_db().collection("users").document(uid).get())


def list_users():
    return [_with_id(snapshot) for snapshot in _db().collection("users").stream()]


def create_user(uid, first_name, last_name, email, address):
    ref = _db().collection("users").document(uid)
    try:
        ref.create({
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "address": address,
            "profilePicturePath": None,
            "gifts": [],
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
    except Conflict:
        raise AlreadyExists(f"user {uid} already exists")
    return get_user(uid)


def update_user(uid, fields):
    """Updates the given snake_case fields. Returns the updated user, or None if it doesn't exist."""
    updates = {USER_FIELDS[name]: value for name, value in fields.items()}
    updates["updatedAt"] = firestore.SERVER_TIMESTAMP
    try:
        _db().collection("users").document(uid).update(updates)
    except NotFound:
        return None
    return get_user(uid)


def delete_user(uid):
    _db().collection("users").document(uid).delete()


def find_user_by_email(email):
    query = _db().collection("users").where(filter=firestore.FieldFilter("email", "==", email)).limit(1)
    return next((_with_id(snapshot) for snapshot in query.stream()), None)


def set_gifts(uid, gifts):
    """Replaces the user's wish list. Returns the updated user, or None if it doesn't exist."""
    stored = [
        {"name": gift["name"], "url": gift.get("url"), "notes": gift.get("notes")}
        for gift in gifts
    ]
    try:
        _db().collection("users").document(uid).update({
            "gifts": stored,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
    except NotFound:
        return None
    return get_user(uid)


# Config

def is_invited(email):
    snapshot = _db().collection("config").document("invites").get()
    emails = (snapshot.to_dict() or {}).get("emails", [])
    return email.lower() in {invited.lower() for invited in emails}


def get_season_config():
    """Returns config/season ({status, revealAt, year}), or None if it hasn't been seeded."""
    snapshot = _db().collection("config").document("season").get()
    return snapshot.to_dict() if snapshot.exists else None


# Assignments

def record_generation(year):
    """Marks the season matched and counts the draw, so emails can say when matches were redrawn."""
    _db().collection("seasons").document(str(year)).set({
        "status": "matched",
        "generatedAt": firestore.SERVER_TIMESTAMP,
        "generation": firestore.Increment(1),
    }, merge=True)


def get_generation(year):
    snapshot = _db().collection("seasons").document(str(year)).get()
    return (snapshot.to_dict() or {}).get("generation", 0)


def _assignments(year):
    return _db().collection("seasons").document(str(year)).collection("assignments")


def get_assignment(year, giver_uid):
    snapshot = _assignments(year).document(giver_uid).get()
    return snapshot.get("receiverUid") if snapshot.exists else None


def list_assignments(year):
    """Returns {giver_uid: receiver_uid} for the season."""
    return {snapshot.id: snapshot.get("receiverUid") for snapshot in _assignments(year).stream()}


def write_assignments(year, mapping):
    # create() fails if a document exists, so this never silently overwrites a match.
    # Regenerating calls delete_assignments first, which also lets the
    # "document created" trigger email everyone again.
    batch = _db().batch()
    for giver_uid, receiver_uid in mapping.items():
        batch.create(_assignments(year).document(giver_uid), {
            "receiverUid": receiver_uid,
            "createdAt": firestore.SERVER_TIMESTAMP,
        })
    batch.commit()


def delete_assignment(year, giver_uid):
    _assignments(year).document(giver_uid).delete()


def delete_assignments(year):
    batch = _db().batch()
    for snapshot in _assignments(year).stream():
        batch.delete(snapshot.reference)
    batch.commit()


# Photos

def create_photo(owner_uid, season, content_type, size_bytes):
    ref = _db().collection("photos").document()
    ref.set({
        "ownerUid": owner_uid,
        "season": season,
        "status": "pending",
        "contentType": content_type,
        "sizeBytes": size_bytes,
        "createdAt": firestore.SERVER_TIMESTAMP,
    })
    return get_photo(ref.id)


def get_photo(photo_id):
    return _with_id(_db().collection("photos").document(photo_id).get())


def list_photos(season, status="ready"):
    query = (
        _db().collection("photos")
        .where(filter=firestore.FieldFilter("season", "==", season))
        .where(filter=firestore.FieldFilter("status", "==", status))
    )
    photos = [_with_id(snapshot) for snapshot in query.stream()]
    # Sorted here rather than with order_by, which would need a composite index
    return sorted(photos, key=lambda photo: photo["createdAt"], reverse=True)


def list_photo_seasons():
    """Returns the seasons that have ready photos, newest first."""
    query = (
        _db().collection("photos")
        .where(filter=firestore.FieldFilter("status", "==", "ready"))
        .select(["season"])
    )
    return sorted({snapshot.get("season") for snapshot in query.stream()}, reverse=True)


def count_photos(owner_uid, season):
    """Counts the user's pending and ready photos, so in-progress uploads count toward the cap."""
    query = (
        _db().collection("photos")
        .where(filter=firestore.FieldFilter("ownerUid", "==", owner_uid))
        .where(filter=firestore.FieldFilter("season", "==", season))
        .where(filter=firestore.FieldFilter("status", "in", ACTIVE_PHOTO_STATUSES))
    )
    return int(query.count().get()[0][0].value)


def list_photos_by_owner(owner_uid):
    query = _db().collection("photos").where(filter=firestore.FieldFilter("ownerUid", "==", owner_uid))
    return [_with_id(snapshot) for snapshot in query.stream()]


def count_photos_by_owner(season):
    """Returns {owner_uid: count} of pending and ready photos for the season, in one query."""
    query = (
        _db().collection("photos")
        .where(filter=firestore.FieldFilter("season", "==", season))
        .where(filter=firestore.FieldFilter("status", "in", ACTIVE_PHOTO_STATUSES))
        .select(["ownerUid"])
    )
    counts = {}
    for snapshot in query.stream():
        owner_uid = snapshot.get("ownerUid")
        counts[owner_uid] = counts.get(owner_uid, 0) + 1
    return counts


def mark_photo_ready(photo_id, display_path, thumb_path):
    _db().collection("photos").document(photo_id).update({
        "status": "ready",
        "displayPath": display_path,
        "thumbPath": thumb_path,
        "processedAt": firestore.SERVER_TIMESTAMP,
    })


def delete_photo(photo_id):
    _db().collection("photos").document(photo_id).delete()


# Questions

def create_question(text):
    # Deliberately takes no asker: questions are anonymous, even to the admin
    _, ref = _db().collection("questions").add({
        "text": text,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "answered": False,
    })
    return _with_id(ref.get())


def list_questions():
    questions = [_with_id(snapshot) for snapshot in _db().collection("questions").stream()]
    return sorted(questions, key=lambda question: question["createdAt"], reverse=True)


# Serializers: map Firestore documents back to the JSON shapes the client expects

def serialize_user(user, profile_picture_url=None):
    # The caller signs profile_picture_url (storage.py) and decides who may see it
    return {
        "id": user["id"],
        "first_name": user.get("firstName"),
        "last_name": user.get("lastName"),
        "email": user.get("email"),
        "address": user.get("address"),
        "profile_picture_url": profile_picture_url,
    }


def serialize_question(question):
    return {
        "id": question["id"],
        "text": question["text"],
        "created_at": question["createdAt"].isoformat(),
        "answered": question.get("answered", False),
    }


def serialize_gifts(user):
    # Gifts have no IDs of their own; their position in the list identifies them
    return [
        {
            "id": position,
            "user_id": user["id"],
            "name": gift["name"],
            "url": gift.get("url"),
            "notes": gift.get("notes"),
            "position": position,
        }
        for position, gift in enumerate(user.get("gifts", []))
    ]
