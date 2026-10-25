from functools import wraps

from firebase_admin import auth
from flask import current_app, g, jsonify, request


def _verify_request_token():
    """Returns the decoded Firebase ID token, None if the request has none, or False if it's invalid."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        return auth.verify_id_token(header.removeprefix("Bearer ").strip())
    except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, auth.RevokedIdTokenError, ValueError):
        return False


def _set_user(token):
    g.uid = token["uid"] if token else None
    g.email = token.get("email", "").lower() if token else None
    # Email-link sign-in verifies the address; never grant admin to an unverified one
    g.is_admin = bool(
        token
        and token.get("email_verified")
        and g.email in current_app.config["ADMIN_EMAILS"]
    )


def require_user(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _verify_request_token()
        if not token:
            return jsonify({"error": "sign in required"}), 401
        _set_user(token)
        return view(*args, **kwargs)
    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _verify_request_token()
        if not token:
            return jsonify({"error": "sign in required"}), 401
        _set_user(token)
        if not g.is_admin:
            return jsonify({"error": "admin only"}), 403
        return view(*args, **kwargs)
    return wrapper


def optional_user(view):
    """For public routes that show more to signed-in users. A bad or expired token counts as signed out."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        _set_user(_verify_request_token() or None)
        return view(*args, **kwargs)
    return wrapper
