from firebase_admin import auth
from flask import Blueprint, abort, g, jsonify, request

import photo_storage
import profile_pictures
import repository
from auth import require_admin, require_user
from season import current_season

users_bp = Blueprint("users", __name__, url_prefix="/api/users")
me_bp = Blueprint("me", __name__, url_prefix="/api/me")

PROFILE_FIELDS = ("first_name", "last_name", "email", "address")


def _serialize(user):
    # Only for the user themself or the admin: everyone else gets no profile picture URL
    return repository.serialize_user(user, profile_pictures.view_url(user.get("profilePicturePath")))


def _clean(data, fields):
    """Returns (values, error) with each field stripped; every listed field must be non-empty."""
    values = {field: str(data.get(field) or "").strip() for field in fields}
    missing = [field for field in fields if not values[field]]
    if missing:
        return None, f"{', '.join(missing)} cannot be empty"
    return values, None


def _email_taken(email, uid):
    existing = repository.find_user_by_email(email)
    return existing is not None and existing["id"] != uid


# The signed-in user's own profile

@me_bp.route("", methods=["GET"])
@require_user
def get_me():
    user = repository.get_user(g.uid)
    if not user:
        # The client treats this as "finish signing up"
        return jsonify({"error": "profile not found"}), 404
    return jsonify({**_serialize(user), "is_admin": g.is_admin})


@me_bp.route("", methods=["POST"])
@require_user
def create_me():
    if not (g.is_admin or repository.is_invited(g.email)):
        return jsonify({"error": "this email hasn't been invited to Secret Santa"}), 403

    values, error = _clean(request.get_json(silent=True) or {}, ("first_name", "last_name", "address"))
    if error:
        return jsonify({"error": error}), 400

    try:
        user = repository.create_user(g.uid, values["first_name"], values["last_name"], g.email, values["address"])
    except repository.AlreadyExists:
        return jsonify({"error": "you've already signed up"}), 409
    return jsonify({**_serialize(user), "is_admin": g.is_admin}), 201


@me_bp.route("", methods=["PATCH"])
@require_user
def update_me():
    data = request.get_json(silent=True) or {}
    # The email comes from sign-in, so it can't be changed here. Sending the same one back is fine.
    if "email" in data and str(data["email"]).strip().lower() != g.email:
        return jsonify({"error": "email can't be changed here"}), 400

    fields = [field for field in ("first_name", "last_name", "address") if field in data]
    values, error = _clean(data, fields)
    if error:
        return jsonify({"error": error}), 400

    user = repository.update_user(g.uid, values)
    if not user:
        return jsonify({"error": "profile not found"}), 404
    return jsonify({**_serialize(user), "is_admin": g.is_admin})


# Admin: everyone's profiles

@users_bp.route("", methods=["GET"])
@require_admin
def list_users():
    return jsonify([_serialize(user) for user in repository.list_users()])


@users_bp.route("/<user_id>", methods=["GET"])
@require_admin
def get_user(user_id):
    user = repository.get_user(user_id) or abort(404)
    return jsonify(_serialize(user))


@users_bp.route("/<user_id>", methods=["PUT"])
@require_admin
def replace_user(user_id):
    values, error = _clean(request.get_json(silent=True) or {}, PROFILE_FIELDS)
    if error:
        return jsonify({"error": error}), 400
    values["email"] = values["email"].lower()
    if _email_taken(values["email"], user_id):
        return jsonify({"error": "a user with that email already exists"}), 409

    user = repository.update_user(user_id, values) or abort(404)
    return jsonify(_serialize(user))


@users_bp.route("/<user_id>", methods=["PATCH"])
@require_admin
def update_user(user_id):
    data = request.get_json(silent=True) or {}
    values, error = _clean(data, [field for field in PROFILE_FIELDS if field in data])
    if error:
        return jsonify({"error": error}), 400
    if "email" in values:
        values["email"] = values["email"].lower()
        if _email_taken(values["email"], user_id):
            return jsonify({"error": "a user with that email already exists"}), 409

    user = repository.update_user(user_id, values) or abort(404)
    return jsonify(_serialize(user))


@users_bp.route("/<user_id>", methods=["DELETE"])
@require_admin
def delete_user(user_id):
    user = repository.get_user(user_id) or abort(404)
    year, _ = current_season()
    assignments = repository.list_assignments(year)

    repository.delete_user(user_id)
    profile_pictures.delete_all_pictures(user_id)
    for photo in repository.list_photos_by_owner(user_id):
        photo_storage.delete_files(photo)
        repository.delete_photo(photo["id"])
    try:
        auth.delete_user(user_id)
    except auth.UserNotFoundError:
        pass

    response = {"deleted": user_id}
    if user_id in assignments or user_id in assignments.values():
        repository.delete_assignment(year, user_id)
        response["warning"] = "Matches were already drawn for this season. Regenerate them so everyone has a match."
    return jsonify(response)


# The signed-in user's profile picture. The browser uploads straight to the bucket,
# and F7 crops it, strips its location data and sets profilePicturePath.

@me_bp.route("/profile-picture", methods=["POST"])
@require_user
def request_profile_picture_upload():
    if not repository.get_user(g.uid):
        return jsonify({"error": "profile not found"}), 404

    data = request.get_json(silent=True) or {}
    content_type = data.get("content_type")
    size = data.get("size")
    if content_type not in profile_pictures.PROFILE_PICTURE_TYPES:
        return jsonify({"error": "profile picture must be a JPEG, PNG, GIF, WebP or HEIC image"}), 400
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= profile_pictures.MAX_PROFILE_PICTURE_BYTES:
        return jsonify({"error": "profile picture must be 5 MB or smaller"}), 400

    picture_id, upload_url, headers = profile_pictures.upload_url(g.uid, content_type)
    return jsonify({"picture_id": picture_id, "upload_url": upload_url, "headers": headers}), 201


@me_bp.route("/profile-picture", methods=["DELETE"])
@require_user
def remove_profile_picture():
    user = repository.get_user(g.uid)
    if not user:
        return jsonify({"error": "profile not found"}), 404
    profile_pictures.delete_picture(user.get("profilePicturePath"))
    user = repository.update_user(g.uid, {"profile_picture_path": None})
    return jsonify({**_serialize(user), "is_admin": g.is_admin})
