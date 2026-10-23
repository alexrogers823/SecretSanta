from flask import Blueprint, jsonify

from matching import generate_derangement
from models import User, db

matches_bp = Blueprint("matches", __name__, url_prefix="/api/matches")


def _serialize_match(user):
    receiver = user.assigned_to
    return {
        "user_id": user.id,
        "assigned_to": receiver.to_dict() if receiver else None,
    }


def _assign_and_commit(users):
    mapping = generate_derangement([u.id for u in users])
    for u in users:
        u.assigned_to_id = mapping[u.id]
    db.session.commit()


@matches_bp.route("", methods=["GET"])
def list_matches():
    return jsonify([_serialize_match(u) for u in User.query.all()])


@matches_bp.route("/<int:user_id>", methods=["GET"])
def get_match(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(_serialize_match(user))


@matches_bp.route("/generate", methods=["POST"])
def generate_matches():
    users = User.query.all()
    already_generated = any(u.assigned_to_id is not None for u in users)

    if not already_generated:
        if len(users) < 2:
            return jsonify({"error": "at least 2 users are required to generate matches"}), 400
        _assign_and_commit(users)

    return jsonify([_serialize_match(u) for u in users])


@matches_bp.route("/regenerate", methods=["POST"])
def regenerate_matches():
    users = User.query.all()
    if len(users) < 2:
        return jsonify({"error": "at least 2 users are required to generate matches"}), 400

    _assign_and_commit(users)
    return jsonify([_serialize_match(u) for u in users])
