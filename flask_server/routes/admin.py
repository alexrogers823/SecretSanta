from flask import Blueprint, jsonify

import profile_pictures
import repository
from auth import require_admin
from season import current_season

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/overview", methods=["GET"])
@require_admin
def overview():
    """Everything the admin page shows, in one call. Questions are separate and never carry an asker."""
    year, _ = current_season()
    users = repository.list_users()
    users_by_id = {user["id"]: user for user in users}
    assignments = repository.list_assignments(year)
    photo_counts = repository.count_photos_by_owner(year)

    def assigned_to(user):
        receiver = users_by_id.get(assignments.get(user["id"]))
        if not receiver:
            return None
        return {"id": receiver["id"], "first_name": receiver.get("firstName"), "last_name": receiver.get("lastName")}

    return jsonify({
        "season": year,
        "generation": repository.get_generation(year),
        "users": [
            {
                **repository.serialize_user(user, profile_pictures.view_url(user.get("profilePicturePath"))),
                "gifts": repository.serialize_gifts(user),
                "assigned_to": assigned_to(user),
                "photo_count": photo_counts.get(user["id"], 0),
            }
            for user in users
        ],
    })
