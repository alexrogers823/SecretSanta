import uuid

from flask import current_app

import storage

MAX_PROFILE_PICTURE_BYTES = 5 * 1024 * 1024
PROFILE_PICTURE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/heic"}


def _bucket():
    return current_app.config["PROFILE_PICTURES_BUCKET"]


def upload_url(uid, content_type):
    """Returns (picture_id, url, headers) for a raw upload. F7 turns it into the user's avatar."""
    picture_id = uuid.uuid4().hex
    url, headers = storage.upload_url(_bucket(), f"uploads/{uid}/{picture_id}", content_type, MAX_PROFILE_PICTURE_BYTES)
    return picture_id, url, headers


def view_url(path):
    return storage.view_url(_bucket(), path) if path else None


def delete_picture(path):
    storage.delete_objects(_bucket(), [path])


def delete_all_pictures(uid):
    storage.delete_prefix(_bucket(), f"uploads/{uid}/")
    storage.delete_prefix(_bucket(), f"avatars/{uid}/")
