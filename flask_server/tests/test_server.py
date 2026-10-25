import pytest

import server
from server import create_app


@pytest.fixture
def clean_env(monkeypatch):
    for name in ("GOOGLE_CLOUD_PROJECT", "FIRESTORE_DATABASE", "PHOTOS_BUCKET", "PROFILE_PICTURES_BUCKET",
                 "ADMIN_EMAILS", "STORAGE_MODE", "ALLOWED_ORIGINS"):
        monkeypatch.delenv(name, raising=False)


def test_defaults_are_this_projects_real_resources(clean_env):
    config = create_app({"TESTING": True}).config
    assert config["GOOGLE_CLOUD_PROJECT"] == "secret-santa-511801"
    assert config["FIRESTORE_DATABASE"] == "secret-santa-database"
    assert config["PHOTOS_BUCKET"] == "secret-santa-photos"
    assert config["PROFILE_PICTURES_BUCKET"] == "secret-santa-profile-photos"
    assert config["ADMIN_EMAILS"] == set()
    assert config["STORAGE_MODE"] == "gcs"
    assert config["ALLOWED_ORIGINS"] == []


def test_settings_come_from_env(clean_env, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", " Admin@Example.com , other@example.com,, ")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("FIRESTORE_DATABASE", "other-db")
    config = create_app({"TESTING": True}).config
    assert config["ADMIN_EMAILS"] == {"admin@example.com", "other@example.com"}
    assert config["ALLOWED_ORIGINS"] == ["http://localhost:3000"]
    assert config["FIRESTORE_DATABASE"] == "other-db"


def test_cors_only_for_allowed_origins(clean_env):
    client = create_app({"TESTING": True, "ALLOWED_ORIGINS": ["http://localhost:3000"]}).test_client()
    allowed = client.get("/api", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Access-Control-Allow-Origin" not in client.get("/api", headers={"Origin": "https://evil.example"}).headers


def test_no_cors_headers_in_production(clean_env):
    client = create_app({"TESTING": True}).test_client()
    assert "Access-Control-Allow-Origin" not in client.get("/api", headers={"Origin": "http://localhost:3000"}).headers


def test_dev_storage_routes_exist_only_in_local_mode(clean_env):
    gcs_rules = {rule.rule for rule in create_app({"TESTING": True}).url_map.iter_rules()}
    local_rules = {rule.rule for rule in create_app({"TESTING": True, "STORAGE_MODE": "local"}).url_map.iter_rules()}
    assert not any(rule.startswith("/api/dev-storage") for rule in gcs_rules)
    assert any(rule.startswith("/api/dev-storage") for rule in local_rules)


def test_initializes_firebase_once_with_the_named_database(clean_env, monkeypatch):
    calls = []
    apps = []

    def get_app():
        if not apps:
            raise ValueError("no app")
        return apps[0]
    monkeypatch.setattr(server.firebase_admin, "get_app", get_app)
    monkeypatch.setattr(server.firebase_admin, "initialize_app",
                        lambda options: apps.append(options) or calls.append(("init", options)))
    monkeypatch.setattr(server.firestore, "client",
                        lambda database_id: calls.append(("client", database_id)) or f"client:{database_id}")

    first = create_app()
    create_app()
    assert calls == [
        ("init", {"projectId": "secret-santa-511801"}),
        ("client", "secret-santa-database"),
        ("client", "secret-santa-database"),
    ]
    assert first.extensions["firestore"] == "client:secret-santa-database"


def test_testing_mode_skips_firebase(clean_env, monkeypatch):
    monkeypatch.setattr(server.firebase_admin, "initialize_app", lambda **kwargs: pytest.fail("initialized"))
    assert "firestore" not in create_app({"TESTING": True}).extensions


def test_basic_routes(client):
    assert client.get("/api").json == {"message": "REPS Secret Santa"}
    about = client.get("/api/about")
    assert about.status_code == 200 and "November 25th" in about.get_data(as_text=True)
