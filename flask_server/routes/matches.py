from flask import Blueprint, g, jsonify, request

import profile_pictures
import repository
from auth import require_admin, require_user
from season import current_season, is_revealed
from shared.matching import NoValidMatchError, generate_derangement

matches_bp = Blueprint("matches", __name__, url_prefix="/api/matches")


def _serialize_matches(year):
    users = repository.list_users()
    users_by_id = {user["id"]: user for user in users}
    assignments = repository.list_assignments(year)
    return [
        {
            "user_id": user["id"],
            "assigned_to": (
                repository.serialize_user(users_by_id[assignments[user["id"]]])
                if assignments.get(user["id"]) in users_by_id
                else None
            ),
        }
        for user in users
    ]


@matches_bp.route("/me", methods=["GET"])
@require_user
def get_my_match():
    year, reveal_at = current_season()
    hidden = {"revealed": False, "reveal_at": reveal_at.isoformat()}
    if not is_revealed(reveal_at):
        return jsonify(hidden)

    receiver_uid = repository.get_assignment(year, g.uid)
    if not receiver_uid:
        # Past the reveal time, but matches haven't been drawn yet
        return jsonify(hidden)

    receiver = repository.get_user(receiver_uid)
    if not receiver:
        # The receiver was deleted after the draw; the admin needs to regenerate
        return jsonify({"revealed": True, "reveal_at": reveal_at.isoformat(), "receiver": None, "gifts": []})

    return jsonify({
        "revealed": True,
        "reveal_at": reveal_at.isoformat(),
        "receiver": {
            "first_name": receiver.get("firstName"),
            "last_name": receiver.get("lastName"),
            "address": receiver.get("address"),
            # The giver may see their receiver's picture, but only after the reveal
            "profile_picture_url": profile_pictures.view_url(receiver.get("profilePicturePath")),
        },
        "gifts": repository.serialize_gifts(receiver),
    })


@matches_bp.route("", methods=["GET"])
@require_admin
def list_matches():
    year, _ = current_season()
    return jsonify(_serialize_matches(year))


@matches_bp.route("/regenerate", methods=["POST"])
@require_admin
def regenerate_matches():
    year, _ = current_season()
    users = repository.list_users()
    if len(users) < 2:
        return jsonify({"error": "at least 2 users are required to generate matches"}), 400

    data = request.get_json(silent=True) or {}
    # Only last year's pairs are avoided; earlier seasons don't affect the draw
    exclusions = set() if data.get("ignore_exclusions") else set(repository.list_assignments(year - 1).items())
    try:
        mapping = generate_derangement([user["id"] for user in users], exclusions)
    except NoValidMatchError:
        return jsonify({
            "error": "every possible draw repeats a pair from last year. "
                     "Send {\"ignore_exclusions\": true} to allow repeats.",
        }), 409

    # Delete, then create: the email function only fires when an assignment is created,
    # so this is what re-emails everyone about their new match
    repository.delete_assignments(year)
    repository.write_assignments(year, mapping)
    repository.record_generation(year)
    return jsonify(_serialize_matches(year))
