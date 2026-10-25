import os
import shutil

from flask import Blueprint, abort, current_app, jsonify, request, send_file

import profile_pictures
import repository
import storage

# Registered only when STORAGE_MODE=local. It stands in for the two private buckets so
# uploads work end to end without signing URLs: the browser PUTs to these routes exactly as
# it would to a signed URL. The real buckets never see dev files.
dev_storage_bp = Blueprint("dev_storage", __name__, url_prefix="/api/dev-storage")

IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}


def _sniff_type(file):
    with open(file, "rb") as handle:
        head = handle.read(12)
    for signature, content_type in IMAGE_SIGNATURES.items():
        if head.startswith(signature):
            return content_type
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp":
        return "image/heic"
    return "application/octet-stream"


def _known_bucket(bucket):
    if bucket not in (current_app.config["PHOTOS_BUCKET"], current_app.config["PROFILE_PICTURES_BUCKET"]):
        abort(404)


def _move(bucket, source, destination):
    target = storage.local_file(bucket, destination)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.move(storage.local_file(bucket, source), target)


def _process_photo(bucket, path):
    # Stands in for F6, minus resizing and EXIF stripping
    parts = path.split("/")
    photo = repository.get_photo(parts[3]) if len(parts) == 4 else None
    if not photo or photo["ownerUid"] != parts[2] or str(photo["season"]) != parts[1]:
        storage.delete_objects(bucket, [path])
        return
    _, season, uid, photo_id = parts
    display_path = f"display/{season}/{uid}/{photo_id}.webp"
    thumb_path = f"thumbs/{season}/{uid}/{photo_id}.webp"
    os.makedirs(os.path.dirname(storage.local_file(bucket, thumb_path)), exist_ok=True)
    shutil.copy(storage.local_file(bucket, path), storage.local_file(bucket, thumb_path))
    _move(bucket, path, display_path)
    repository.mark_photo_ready(photo_id, display_path, thumb_path)


def _process_profile_picture(bucket, path):
    # Stands in for F7, minus cropping and EXIF stripping
    parts = path.split("/")
    user = repository.get_user(parts[1]) if len(parts) == 3 else None
    if not user:
        storage.delete_objects(bucket, [path])
        return
    _, uid, picture_id = parts
    avatar_path = f"avatars/{uid}/{picture_id}.webp"
    _move(bucket, path, avatar_path)
    profile_pictures.delete_picture(user.get("profilePicturePath"))
    repository.update_user(uid, {"profile_picture_path": avatar_path})


@dev_storage_bp.route("/<bucket>/<path:path>", methods=["PUT"])
def put_object(bucket, path):
    _known_bucket(bucket)
    file = storage.local_file(bucket, path)
    if not file or not path.startswith("uploads/"):
        abort(403)

    # Enforce the same limits a signed URL would
    _, _, max_bytes = request.headers.get("x-goog-content-length-range", "").partition(",")
    if not request.content_type or not max_bytes.isdigit():
        return jsonify({"error": "missing Content-Type or x-goog-content-length-range header"}), 400
    data = request.get_data()
    if len(data) > int(max_bytes):
        return jsonify({"error": "file is too large"}), 400

    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "wb") as handle:
        handle.write(data)

    if bucket == current_app.config["PHOTOS_BUCKET"]:
        _process_photo(bucket, path)
    else:
        _process_profile_picture(bucket, path)
    return "", 200


@dev_storage_bp.route("/<bucket>/<path:path>", methods=["GET"])
def get_object(bucket, path):
    _known_bucket(bucket)
    file = storage.local_file(bucket, path)
    if not file or not os.path.isfile(file):
        abort(404)
    return send_file(file, mimetype=_sniff_type(file))
