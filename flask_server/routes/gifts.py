from urllib.parse import urlparse

from flask import Blueprint, g, jsonify, request

import repository
from auth import require_user

gifts_bp = Blueprint("gifts", __name__, url_prefix="/api/me/gifts")

MAX_GIFTS = 4  # keep in sync with client GIFT_OPTIONS length


def _is_web_url(url):
    # Only http(s): a javascript: URL would run in the gift-giver's browser when they click it
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


@gifts_bp.route("", methods=["GET"])
@require_user
def list_gifts():
    user = repository.get_user(g.uid)
    if not user:
        return jsonify({"error": "profile not found"}), 404
    return jsonify(repository.serialize_gifts(user))


@gifts_bp.route("", methods=["PUT"])
@require_user
def replace_gifts():
    data = request.get_json(silent=True) or {}
    payload = data.get("gifts")

    if not isinstance(payload, list):
        return jsonify({"error": "gifts must be a list"}), 400
    if len(payload) > MAX_GIFTS:
        return jsonify({"error": f"a maximum of {MAX_GIFTS} gifts is allowed"}), 400

    new_gifts = []
    for index, item in enumerate(payload):
        item = item if isinstance(item, dict) else {}
        name = str(item.get("name") or "").strip()
        url = str(item.get("url") or "").strip() or None
        notes = str(item.get("notes") or "").strip() or None
        if not name:
            return jsonify({"error": f"gift {index + 1} is missing a name"}), 400
        if url and not _is_web_url(url):
            return jsonify({"error": f"gift {index + 1} link must start with http:// or https://"}), 400
        new_gifts.append({"name": name, "url": url, "notes": notes})

    user = repository.set_gifts(g.uid, new_gifts)
    if not user:
        return jsonify({"error": "profile not found"}), 404
    return jsonify(repository.serialize_gifts(user))
