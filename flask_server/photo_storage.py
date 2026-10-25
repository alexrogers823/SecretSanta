from flask import current_app

import storage

MAX_PHOTO_BYTES = 15 * 1024 * 1024
MAX_PHOTOS_PER_SEASON = 25
MAX_FILES_PER_REQUEST = 10
PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}


def _bucket():
    return current_app.config["PHOTOS_BUCKET"]


def upload_path(photo):
    return f"uploads/{photo['season']}/{photo['ownerUid']}/{photo['id']}"


def upload_url(photo):
    return storage.upload_url(_bucket(), upload_path(photo), photo["contentType"], MAX_PHOTO_BYTES)


def view_urls(paths):
    return storage.view_urls(_bucket(), paths)


def delete_files(photo):
    storage.delete_objects(_bucket(), [upload_path(photo), photo.get("displayPath"), photo.get("thumbPath")])
