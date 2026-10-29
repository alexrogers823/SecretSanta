"""Event-driven Cloud Run functions (plan §3 and Phase 3). Each one is an entry point for
`gcloud functions deploy --entry-point=<name>`.

Every handler is idempotent: events can be delivered more than once.
"""
import base64
import binascii
import json
import logging
import os
from datetime import datetime

import functions_framework
from firebase_admin import firestore
from google.api_core.exceptions import NotFound

import images
import mailer
import messages
import store
from shared.matching import NoValidMatchError, generate_derangement

logger = logging.getLogger(__name__)

PHOTO_CACHE_CONTROL = "private, max-age=3600"


def _admin_emails():
    return [email.strip() for email in os.environ.get("ADMIN_EMAILS", "").split(",") if email.strip()]


def _pubsub_action(cloud_event):
    """The Scheduler jobs publish {"action": "..."} to season-events (an "action" attribute also works)."""
    message = (cloud_event.data or {}).get("message") or {}
    action = (message.get("attributes") or {}).get("action")
    if action:
        return action
    try:
        payload = json.loads(base64.b64decode(message.get("data") or "") or b"{}")
    except (binascii.Error, ValueError):
        return None
    return payload.get("action") if isinstance(payload, dict) else None


def _document_path(cloud_event):
    """'seasons/2026/assignments/uid' from a Firestore event's subject ('documents/seasons/...')."""
    return cloud_event["subject"].split("documents/", 1)[1]


def _delete_quietly(blob):
    try:
        blob.delete()
    except NotFound:
        pass


# F1: draw matches on Nov 25 (Scheduler -> season-events)

@functions_framework.cloud_event
def generate_matches(cloud_event):
    if _pubsub_action(cloud_event) == "generate_matches":
        store.run_once(f"generate_matches:{cloud_event['id']}", _generate_matches)


def _generate_matches():
    db = store.db()
    year, _ = store.current_season()
    season = db.collection("seasons").document(str(year))
    assignments = season.collection("assignments")

    if any(True for _ in assignments.stream()):
        logger.info("Matches for %s already exist; nothing to do", year)
        return

    user_ids = [snapshot.id for snapshot in db.collection("users").stream()]
    if len(user_ids) < 2:
        mailer.send(_admin_emails(), *messages.not_enough_people(year, len(user_ids)))
        return

    # Only last year's pairs are avoided; earlier seasons don't affect the draw
    last_year = db.collection("seasons").document(str(year - 1)).collection("assignments")
    exclusions = {(snapshot.id, (snapshot.to_dict() or {}).get("receiverUid")) for snapshot in last_year.stream()}
    try:
        mapping = generate_derangement(user_ids, exclusions)
    except NoValidMatchError:
        mailer.send(_admin_emails(), *messages.no_valid_draw(year))
        return

    batch = db.batch()
    for giver_uid, receiver_uid in mapping.items():
        # create() fails rather than overwrite, and each creation triggers notify_match
        batch.create(assignments.document(giver_uid), {"receiverUid": receiver_uid, "createdAt": firestore.SERVER_TIMESTAMP})
    batch.set(season, {"status": "matched", "generatedAt": firestore.SERVER_TIMESTAMP, "generation": 1}, merge=True)
    batch.set(db.collection("config").document("season"), {"status": "matched"}, merge=True)
    batch.commit()
    logger.info("Drew %d matches for %s", len(mapping), year)


# F2: email each giver when their assignment is created (Firestore trigger)

@functions_framework.cloud_event
def notify_match(cloud_event):
    path = _document_path(cloud_event)
    store.run_once(f"notify_match:{cloud_event['id']}", lambda: _notify_match(path))


def _notify_match(path):
    _, year, _, giver_uid = path.split("/")
    db = store.db()
    season = db.collection("seasons").document(year)
    assignment = season.collection("assignments").document(giver_uid)

    snapshot = assignment.get()
    # Missing: deleted by a regenerate before this event arrived. notifiedAt: already emailed.
    if not snapshot.exists or (snapshot.to_dict() or {}).get("notifiedAt"):
        return

    giver = db.collection("users").document(giver_uid).get()
    email = (giver.to_dict() or {}).get("email") if giver.exists else None
    if not email:
        logger.warning("No email for giver %s; skipping", giver_uid)
        return

    generation = (season.get().to_dict() or {}).get("generation", 1)
    config_year, reveal_at = store.current_season()
    if str(config_year) != year:
        # An assignment for a season other than the configured one; use that year's default reveal time
        reveal_at = datetime(int(year), 11, 25, 12, tzinfo=store.EASTERN_STANDARD_TIME)
    subject, body = messages.match_ready(
        (giver.to_dict() or {}).get("firstName"),
        redrawn=generation > 1,
        revealed=store.now() >= reveal_at,
        reveal_at=reveal_at,
    )
    mailer.send([email], subject, body)
    assignment.update({"notifiedAt": firestore.SERVER_TIMESTAMP})


# F3: email the admin each new anonymous question (Firestore trigger)

@functions_framework.cloud_event
def notify_admin_question(cloud_event):
    question_id = _document_path(cloud_event).split("/")[1]
    store.run_once(f"notify_admin_question:{cloud_event['id']}", lambda: _notify_admin_question(question_id))


def _notify_admin_question(question_id):
    question = store.db().collection("questions").document(question_id)
    snapshot = question.get()
    if not snapshot.exists or (snapshot.to_dict() or {}).get("notifiedAt"):
        return
    admins = _admin_emails()
    if not admins:
        logger.warning("ADMIN_EMAILS isn't set; can't send the question")
        return
    # The question has no asker, by design: there's nothing to log or include but the text
    mailer.send(admins, *messages.new_question(snapshot.to_dict().get("text", "")))
    question.update({"notifiedAt": firestore.SERVER_TIMESTAMP})


# F4 (and F5): wish list reminders and closing the season (Scheduler -> season-events)

@functions_framework.cloud_event
def gift_reminder(cloud_event):
    action = _pubsub_action(cloud_event)
    if action == "gift_reminder":
        _send_gift_reminders(cloud_event["id"])
    elif action == "close_season":
        store.run_once(f"close_season:{cloud_event['id']}", _close_season)


def _send_gift_reminders(event_id):
    _, reveal_at = store.current_season()
    if store.now() >= reveal_at:
        return  # too late to matter

    failures = 0
    for snapshot in store.db().collection("users").stream():
        user = snapshot.to_dict() or {}
        if user.get("gifts") or not user.get("email"):
            continue
        # One claim per person, so a redelivery or retry doesn't email anyone twice
        try:
            store.run_once(
                f"gift_reminder:{event_id}:{snapshot.id}",
                lambda user=user: mailer.send([user["email"]], *messages.gift_reminder(user.get("firstName"), reveal_at)),
            )
        except Exception:
            logger.exception("Couldn't send a gift reminder to %s", snapshot.id)
            failures += 1
    if failures:
        raise RuntimeError(f"{failures} gift reminder(s) failed")


def _close_season():
    store.db().collection("config").document("season").set({"status": "closed"}, merge=True)


# F6: make photos safe to show (Storage object finalized on the photos bucket)

@functions_framework.cloud_event
def process_photo(cloud_event):
    name = cloud_event.data["name"]
    # Its own output lands in this bucket too; reacting to it would loop forever
    if not name.startswith("uploads/"):
        return

    bucket = store.bucket(cloud_event.data["bucket"])
    upload = bucket.blob(name)
    parts = name.split("/")
    photo_ref = store.db().collection("photos").document(parts[3]) if len(parts) == 4 else None
    snapshot = photo_ref.get() if photo_ref else None
    photo = (snapshot.to_dict() or {}) if snapshot and snapshot.exists else None

    # An upload nobody asked for, or one whose path doesn't match its photo record
    if not photo or photo.get("ownerUid") != parts[2] or str(photo.get("season")) != parts[1]:
        _delete_quietly(upload)
        return
    if photo.get("status") in ("ready", "rejected"):
        _delete_quietly(upload)  # already handled; a redelivery
        return

    try:
        raw = upload.download_as_bytes()
    except NotFound:
        return  # processed and cleaned up by an earlier delivery

    try:
        display, thumb = images.photo_variants(raw)
    except images.InvalidImage:
        logger.info("Rejected photo %s: not a readable image", parts[3])
        _delete_quietly(upload)
        try:
            photo_ref.update({"status": "rejected", "processedAt": firestore.SERVER_TIMESTAMP})
        except NotFound:
            pass  # the owner deleted it meanwhile
        return

    _, season, uid, photo_id = parts
    display_path = f"display/{season}/{uid}/{photo_id}.webp"
    thumb_path = f"thumbs/{season}/{uid}/{photo_id}.webp"
    for path, data in ((display_path, display), (thumb_path, thumb)):
        blob = bucket.blob(path)
        blob.cache_control = PHOTO_CACHE_CONTROL
        blob.upload_from_string(data, content_type="image/webp")

    try:
        photo_ref.update({
            "status": "ready",
            "displayPath": display_path,
            "thumbPath": thumb_path,
            "processedAt": firestore.SERVER_TIMESTAMP,
        })
    except NotFound:
        # The owner deleted the photo while it was being processed
        for path in (display_path, thumb_path):
            _delete_quietly(bucket.blob(path))
    # Deleted last: if this fails, a redelivery finds the photo ready and just cleans up
    _delete_quietly(upload)


# F7: make profile pictures safe to show (Storage object finalized on the profile-pictures bucket)

@functions_framework.cloud_event
def process_profile_picture(cloud_event):
    name = cloud_event.data["name"]
    if not name.startswith("uploads/"):
        return

    bucket = store.bucket(cloud_event.data["bucket"])
    upload = bucket.blob(name)
    parts = name.split("/")
    user_ref = store.db().collection("users").document(parts[1]) if len(parts) == 3 else None
    snapshot = user_ref.get() if user_ref else None
    if not snapshot or not snapshot.exists:
        _delete_quietly(upload)
        return

    _, uid, picture_id = parts
    avatar_path = f"avatars/{uid}/{picture_id}.webp"
    previous_path = (snapshot.to_dict() or {}).get("profilePicturePath")
    if previous_path == avatar_path:
        _delete_quietly(upload)  # already handled; a redelivery
        return

    try:
        raw = upload.download_as_bytes()
    except NotFound:
        return

    try:
        avatar = images.avatar(raw)
    except images.InvalidImage:
        logger.info("Rejected profile picture for %s: not a readable image", uid)
        _delete_quietly(upload)
        return

    blob = bucket.blob(avatar_path)
    blob.cache_control = PHOTO_CACHE_CONTROL
    blob.upload_from_string(avatar, content_type="image/webp")
    try:
        user_ref.update({"profilePicturePath": avatar_path, "updatedAt": firestore.SERVER_TIMESTAMP})
    except NotFound:
        _delete_quietly(blob)  # the account was deleted meanwhile
    else:
        if previous_path:
            _delete_quietly(bucket.blob(previous_path))
    _delete_quietly(upload)
