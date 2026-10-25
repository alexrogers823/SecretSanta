import pytest
from firebase_admin import auth as firebase_auth
from flask import Flask, g, jsonify

import auth


@pytest.fixture
def auth_app(tokens):
    """A tiny app with one route per decorator, so the decorators are tested on their own."""
    app = Flask(__name__)
    app.config["ADMIN_EMAILS"] = {"admin@example.com"}

    def whoami():
        return jsonify({"uid": g.uid, "email": g.email, "is_admin": g.is_admin})

    app.add_url_rule("/user", "user", auth.require_user(whoami))
    app.add_url_rule("/admin", "admin", auth.require_admin(whoami))
    app.add_url_rule("/optional", "optional", auth.optional_user(whoami))
    return app.test_client()


def test_require_user_rejects_missing_malformed_and_invalid_tokens(auth_app):
    assert auth_app.get("/user").status_code == 401
    assert auth_app.get("/user", headers={"Authorization": "Basic abc"}).status_code == 401
    assert auth_app.get("/user", headers={"Authorization": "Bearer nope"}).status_code == 401


@pytest.mark.parametrize("error", [
    firebase_auth.ExpiredIdTokenError("expired", cause=None),
    firebase_auth.RevokedIdTokenError("revoked"),
    ValueError("malformed"),
])
def test_require_user_rejects_expired_and_revoked_tokens(auth_app, monkeypatch, error):
    def raise_error(token):
        raise error
    monkeypatch.setattr(auth.auth, "verify_id_token", raise_error)
    assert auth_app.get("/user", headers={"Authorization": "Bearer x"}).status_code == 401


def test_require_user_sets_uid_and_lowercased_email(auth_app, sign_in):
    response = auth_app.get("/user", headers=sign_in("u1", "Ann@Example.com"))
    assert response.status_code == 200
    assert response.json == {"uid": "u1", "email": "ann@example.com", "is_admin": False}


def test_require_admin(auth_app, sign_in):
    assert auth_app.get("/admin").status_code == 401
    assert auth_app.get("/admin", headers=sign_in("u1", "someone@example.com")).status_code == 403
    response = auth_app.get("/admin", headers=sign_in("a1", "ADMIN@example.com"))
    assert response.status_code == 200 and response.json["is_admin"] is True


def test_unverified_admin_email_is_not_admin(auth_app, sign_in):
    headers = sign_in("a1", "admin@example.com", verified=False)
    assert auth_app.get("/admin", headers=headers).status_code == 403
    assert auth_app.get("/user", headers=headers).json["is_admin"] is False


def test_optional_user_signed_out_and_with_a_bad_token(auth_app):
    signed_out = {"uid": None, "email": None, "is_admin": False}
    assert auth_app.get("/optional").json == signed_out
    assert auth_app.get("/optional", headers={"Authorization": "Bearer nope"}).json == signed_out


def test_optional_user_signed_in(auth_app, sign_in):
    assert auth_app.get("/optional", headers=sign_in("u1")).json["uid"] == "u1"
