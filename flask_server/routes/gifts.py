from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from models import Gift, User, db

gifts_bp = Blueprint("gifts", __name__, url_prefix="/api/users/<int:user_id>/gifts")

MAX_GIFTS = 4  # keep in sync with client GIFT_OPTIONS length


@gifts_bp.route("", methods=["GET"])
def list_gifts(user_id):
    User.query.get_or_404(user_id)
    gifts = Gift.query.filter_by(user_id=user_id).order_by(Gift.position).all()
    return jsonify([gift.to_dict() for gift in gifts])


@gifts_bp.route("", methods=["PUT"])
def replace_gifts(user_id):
    User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}
    payload = data.get("gifts")

    if not isinstance(payload, list):
        return jsonify({"error": "gifts must be a list"}), 400
    if len(payload) > MAX_GIFTS:
        return jsonify({"error": f"a maximum of {MAX_GIFTS} gifts is allowed"}), 400

    new_gifts = []
    for index, item in enumerate(payload):
        item = item or {}
        name = item.get("name")
        if not name or not str(name).strip():
            return jsonify({"error": f"gift {index + 1} is missing a name"}), 400
        new_gifts.append(Gift(
            user_id=user_id,
            name=str(name).strip(),
            url=(item.get("url") or None),
            notes=(item.get("notes") or None),
            position=index,
        ))

    Gift.query.filter_by(user_id=user_id).delete()
    db.session.add_all(new_gifts)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "unable to save gifts"}), 409

    return jsonify([gift.to_dict() for gift in new_gifts])
