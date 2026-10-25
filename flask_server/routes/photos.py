import threading
import time

from flask import Blueprint, abort, g, jsonify, request

import photo_storage
import repository
from auth import optional_user, require_user
from season import current_season

photos_bp = Blueprint("photos", __name__, url_prefix="/api/photos")

# The gallery is public, and on Cloud Run every signed URL is an IAM API call, so visitors
# share a cached list for 10 minutes. The URLs inside last an hour, so they stay valid.
CACHE_SECONDS = 10 * 60
_cache = {}
_cache_lock = threading.Lock()


def _cached(key, build, refresh=False):
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get(key)
    if entry and not refresh and entry[0] > now:
        return entry[1]
    value = build()
    with _cache_lock:
        _cache[key] = (now + CACHE_SECONDS, value)
    return value


def _forget(season):
    with _cache_lock:
        _cache.pop(("photos", season), None)
        _cache.pop("seasons", None)


def _signed_photos(season):
    photos = repository.list_photos(season)
    urls = photo_storage.view_urls([path for photo in photos for path in (photo["thumbPath"], photo["displayPath"])])
    return [
        {
            "id": photo["id"],
            "owner_uid": photo["ownerUid"],
            "thumb_url": urls[2 * index],
            "display_url": urls[2 * index + 1],
            "created_at": photo["createdAt"].isoformat(),
        }
        for index, photo in enumerate(photos)
    ]


@photos_bp.route("", methods=["GET"])
@optional_user
def list_photos():
    current_year, _ = current_season()
    season = request.args.get("season", type=int) or current_year
    # Members always get a fresh list, so their own uploads show up as soon as they're processed.
    # That also refreshes the cached copy visitors see.
    signed_in = g.uid is not None
    photos = _cached(("photos", season), lambda: _signed_photos(season), refresh=signed_in)
    seasons = _cached("seasons", repository.list_photo_seasons, refresh=signed_in)

    if signed_in:
        first_names = {user["id"]: user.get("firstName") for user in repository.list_users()}
        photos = [
            {
                **photo,
                "owner_first_name": first_names.get(photo["owner_uid"]),
                "can_delete": photo["owner_uid"] == g.uid or g.is_admin,
            }
            for photo in photos
        ]

    return jsonify({
        "season": season,
        "seasons": sorted(set(seasons) | {current_year}, reverse=True),
        # Visitors never see who uploaded a photo
        "photos": [{key: value for key, value in photo.items() if key != "owner_uid"} for photo in photos],
    })


@photos_bp.route("/uploads", methods=["POST"])
@require_user
def create_uploads():
    if not repository.get_user(g.uid):
        return jsonify({"error": "finish signing up before uploading photos"}), 403

    files = (request.get_json(silent=True) or {}).get("files")
    if not isinstance(files, list) or not files:
        return jsonify({"error": "files must be a non-empty list"}), 400
    if len(files) > photo_storage.MAX_FILES_PER_REQUEST:
        return jsonify({"error": f"upload up to {photo_storage.MAX_FILES_PER_REQUEST} photos at a time"}), 400

    for index, file in enumerate(files):
        file = file if isinstance(file, dict) else {}
        size = file.get("size")
        if file.get("content_type") not in photo_storage.PHOTO_TYPES:
            return jsonify({"error": f"file {index + 1} must be a JPEG, PNG, WebP or HEIC image"}), 400
        if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= photo_storage.MAX_PHOTO_BYTES:
            return jsonify({"error": f"file {index + 1} must be 15 MB or smaller"}), 400

    season, _ = current_season()
    remaining = photo_storage.MAX_PHOTOS_PER_SEASON - repository.count_photos(g.uid, season)
    if len(files) > remaining:
        return jsonify({
            "error": f"you can upload {photo_storage.MAX_PHOTOS_PER_SEASON} photos per season, "
                     f"and have {max(remaining, 0)} left",
        }), 400

    uploads = []
    for file in files:
        photo = repository.create_photo(g.uid, season, file["content_type"], file["size"])
        upload_url, headers = photo_storage.upload_url(photo)
        uploads.append({"photo_id": photo["id"], "upload_url": upload_url, "headers": headers})
    return jsonify(uploads), 201


@photos_bp.route("/<photo_id>", methods=["DELETE"])
@require_user
def delete_photo(photo_id):
    photo = repository.get_photo(photo_id) or abort(404)
    if photo["ownerUid"] != g.uid and not g.is_admin:
        abort(403)

    photo_storage.delete_files(photo)
    repository.delete_photo(photo_id)
    _forget(photo["season"])
    return "", 204
