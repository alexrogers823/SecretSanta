import pytest
from firebase_admin import auth as firebase_auth

import auth
import storage
from routes import photos as photo_routes
from server import create_app
from tests.fakes import FakeRepository, install

ADMIN_EMAIL = "admin@example.com"
SEASON = 2026


@pytest.fixture
def repo(monkeypatch):
    fake = FakeRepository()
    install(monkeypatch, fake)
    fake.season_config = {"year": SEASON}  # revealAt is set per test where it matters
    return fake


@pytest.fixture
def app(repo, tmp_path):
    app = create_app({
        "TESTING": True,
        "ADMIN_EMAILS": {ADMIN_EMAIL},
        "ALLOWED_ORIGINS": [],
        # Local mode keeps uploads in tmp_path, so storage needs no cloud credentials
        "STORAGE_MODE": "local",
        "SERVER_NAME": "localhost",
    })
    app.instance_path = str(tmp_path)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_module_state():
    # Module-level caches would otherwise leak between tests
    photo_routes._cache.clear()
    storage._credentials = None
    storage._client = None
    yield
    photo_routes._cache.clear()


@pytest.fixture
def tokens(monkeypatch):
    """Fake Firebase ID tokens: register one with sign_in(), then send its headers."""
    valid = {}

    def verify_id_token(token):
        if token not in valid:
            raise firebase_auth.InvalidIdTokenError("invalid token")
        return valid[token]

    monkeypatch.setattr(auth.auth, "verify_id_token", verify_id_token)
    return valid


@pytest.fixture
def sign_in(tokens):
    def sign_in(uid, email=None, verified=True):
        token = f"token-{uid}"
        tokens[token] = {"uid": uid, "email": email or f"{uid}@example.com", "email_verified": verified}
        return {"Authorization": f"Bearer {token}"}
    return sign_in


@pytest.fixture
def admin_headers(repo, sign_in):
    repo.add_user("admin", "Ad", "Min", email=ADMIN_EMAIL)
    return sign_in("admin", ADMIN_EMAIL)
