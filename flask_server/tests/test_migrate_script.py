"""The parts of scripts/migrate_sqlite_to_firestore.py that don't need Firebase.

Running the migration itself needs the emulators, so it belongs with the integration tests.
"""
import importlib.util
import os

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "migrate_sqlite_to_firestore.py")


@pytest.fixture
def migrate():
    spec = importlib.util.spec_from_file_location("migrate_sqlite_to_firestore", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("url, expected", [
    ("https://shop.example/a", "https://shop.example/a"),
    ("http://shop.example", "http://shop.example"),
    ("javascript:alert(1)", None),
    ("shop.example", None),
    ("", None),
    (None, None),
])
def test_only_web_links_are_copied(migrate, url, expected):
    assert migrate.web_url_or_none(url) == expected


def test_refuses_the_real_project_without_production_flag(migrate, monkeypatch, capsys):
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.delenv("FIREBASE_AUTH_EMULATOR_HOST", raising=False)
    monkeypatch.setattr(migrate.firebase_admin, "initialize_app", lambda **kwargs: pytest.fail("touched Firebase"))
    monkeypatch.setattr("sys.argv", ["migrate", "--write"])
    with pytest.raises(SystemExit):
        migrate.main()
    assert "--production" in capsys.readouterr().err


def test_needs_both_emulators_to_count_as_safe(migrate, monkeypatch):
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
    monkeypatch.delenv("FIREBASE_AUTH_EMULATOR_HOST", raising=False)
    monkeypatch.setattr(migrate.firebase_admin, "initialize_app", lambda **kwargs: pytest.fail("touched Firebase"))
    monkeypatch.setattr("sys.argv", ["migrate"])
    with pytest.raises(SystemExit):
        migrate.main()
