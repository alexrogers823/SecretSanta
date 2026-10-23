from flask import Blueprint, abort, jsonify, request, send_from_directory
from sqlalchemy.exc import IntegrityError

from models import User, db
from profile_pictures import (
    MAX_PROFILE_PICTURE_BYTES,
    delete_profile_picture,
    detect_image_extension,
    profile_picture_folder,
    save_profile_picture,
)

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.route("", methods=["GET"])
def list_users():
    query = User.query
    first_name = request.args.get("first_name")
    email = request.args.get("email")

    if first_name:
        query = query.filter_by(first_name=first_name)
    if email:
        query = query.filter_by(email=email)

    return jsonify([user.to_dict() for user in query.all()])


@users_bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@users_bp.route("", methods=["POST"])
def create_user():
    data = request.get_json(silent=True) or {}
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    address = data.get("address")

    if not first_name or not last_name or not email or not address:
        return jsonify({"error": "first_name, last_name, email, and address are required"}), 400

    user = User(first_name=first_name, last_name=last_name, email=email, address=address)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "a user with that email already exists"}), 409

    return jsonify(user.to_dict()), 201


@users_bp.route("/<int:user_id>", methods=["PUT"])
def replace_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    address = data.get("address")

    if not first_name or not last_name or not email or not address:
        return jsonify({"error": "first_name, last_name, email, and address are required"}), 400

    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.address = address
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "a user with that email already exists"}), 409

    return jsonify(user.to_dict())


@users_bp.route("/<int:user_id>", methods=["PATCH"])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    for field in ("first_name", "last_name"):
        if field in data and not data[field]:
            return jsonify({"error": f"{field} cannot be empty"}), 400

    if "first_name" in data:
        user.first_name = data["first_name"]
    if "last_name" in data:
        user.last_name = data["last_name"]
    if "email" in data:
        user.email = data["email"]
    if "address" in data:
        user.address = data["address"]

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "a user with that email already exists"}), 409

    return jsonify(user.to_dict())


@users_bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    profile_picture = user.profile_picture
    db.session.delete(user)
    db.session.commit()
    delete_profile_picture(profile_picture)
    return "", 204


@users_bp.route("/<int:user_id>/profile-picture", methods=["GET"])
def get_profile_picture(user_id):
    user = User.query.get_or_404(user_id)
    if not user.profile_picture:
        abort(404)
    return send_from_directory(profile_picture_folder(), user.profile_picture)


@users_bp.route("/<int:user_id>/profile-picture", methods=["PUT"])
def upload_profile_picture(user_id):
    user = User.query.get_or_404(user_id)
    file = request.files.get("profile_picture")
    if not file:
        return jsonify({"error": "profile_picture file is required"}), 400

    data = file.read(MAX_PROFILE_PICTURE_BYTES + 1)
    if len(data) > MAX_PROFILE_PICTURE_BYTES:
        return jsonify({"error": "profile picture must be 5 MB or smaller"}), 413

    extension = detect_image_extension(data)
    if not extension:
        return jsonify({"error": "profile picture must be a JPEG, PNG, GIF, or WebP image"}), 400

    previous_picture = user.profile_picture
    user.profile_picture = save_profile_picture(user.id, data, extension)
    db.session.commit()
    delete_profile_picture(previous_picture)

    return jsonify(user.to_dict())


@users_bp.route("/<int:user_id>/profile-picture", methods=["DELETE"])
def remove_profile_picture(user_id):
    user = User.query.get_or_404(user_id)
    previous_picture = user.profile_picture
    user.profile_picture = None
    db.session.commit()
    delete_profile_picture(previous_picture)

    return jsonify(user.to_dict())
