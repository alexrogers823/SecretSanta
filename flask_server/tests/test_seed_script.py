"""The parts of scripts/seed_config.py that don't need Firebase."""
import importlib.util
import os
from datetime import datetime, timedelta, timezone

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "seed_config.py")


@pytest.fixture
def seed():
    spec = importlib.util.spec_from_file_location("seed_config", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def no_firebase(seed, monkeypatch):
    monkeypatch.setattr(seed.firebase_admin, "initialize_app", lambda **kwargs: pytest.fail("touched Firebase"))


def write_invites(tmp_path, text):
    path = tmp_path / "invites.txt"
    path.write_text(text)
    return str(path)


def test_reads_emails_skipping_comments_blanks_and_duplicates(seed, tmp_path):
    path = write_invites(tmp_path, "# the guys\nAnn@Example.com\n\n  bo@example.com  # Bo\nann@example.com\n")
    assert seed.read_emails(path) == ["ann@example.com", "bo@example.com"]


@pytest.mark.parametrize("line", ["ann", "ann@example", "@example.com", "ann bo@example.com"])
def test_rejects_lines_that_are_not_emails(seed, tmp_path, line):
    with pytest.raises(ValueError, match="line 1"):
        seed.read_emails(write_invites(tmp_path, line + "\n"))


def test_default_reveal_is_nov_25_noon_eastern(seed):
    reveal_at = seed.parse_reveal(seed.DEFAULT_REVEAL)
    assert reveal_at == datetime(2026, 11, 25, 17, tzinfo=timezone.utc)
    assert reveal_at.utcoffset() == timedelta(hours=-5)


def test_reveal_needs_a_utc_offset(seed):
    with pytest.raises(ValueError, match="UTC offset"):
        seed.parse_reveal("2026-11-25T12:00")


def test_refuses_the_real_project_without_production_flag(seed, no_firebase, monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.setattr("sys.argv", ["seed", "--write", "--invites", write_invites(tmp_path, "a@example.com\n")])
    with pytest.raises(SystemExit):
        seed.main()
    assert "--production" in capsys.readouterr().err


def test_production_flag_refuses_an_emulator_left_set_by_dotenv(seed, no_firebase, monkeypatch, capsys, tmp_path):
    # pipenv loads flask_server/.env; without this check the "production" write went to the emulator
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
    monkeypatch.setattr("sys.argv", ["seed", "--production", "--write", "--invites", write_invites(tmp_path, "a@example.com\n")])
    with pytest.raises(SystemExit):
        seed.main()
    assert "PIPENV_DONT_LOAD_ENV=1" in capsys.readouterr().err


def test_dry_run_lists_the_changes_without_touching_firebase(seed, no_firebase, monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.setattr("sys.argv", ["seed", "--production", "--invites", write_invites(tmp_path, "a@example.com\n")])
    seed.main()
    out = capsys.readouterr().out
    assert "a@example.com" in out and "revealAt 2026-11-25T12:00:00-05:00" in out and "Nothing saved" in out


def test_an_empty_invites_file_is_an_error(seed, no_firebase, monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", ["seed", "--production", "--invites", write_invites(tmp_path, "# nobody yet\n")])
    with pytest.raises(SystemExit):
        seed.main()
