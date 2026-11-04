"""What `gcloud run deploy --source flask_server` uploads (.gcloudignore) and what ends up in the
image (.dockerignore). A file dropped by either deploys "successfully" and then fails: without the
Dockerfile the build can't start, and without shared/ the app crashes on startup.
"""
from fnmatch import fnmatch
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parent.parent


def ignore_patterns(name):
    lines = (SERVER_DIR / name).read_text().splitlines()
    return [line.strip().rstrip("/") for line in lines if line.strip() and not line.startswith("#")]


def is_ignored(path, patterns):
    parts = path.split("/")
    return any(fnmatch(path, pattern) or any(fnmatch(part, pattern) for part in parts) for pattern in patterns)


APP_FILES = ["server.py", "requirements.txt", "routes/users.py", "repository.py", "storage.py", "shared/matching.py"]
PRIVATE_FILES = [".env", "instance/secret_santa.db", "instance/dev_storage/x.webp"]


@pytest.mark.parametrize("path", APP_FILES + ["Dockerfile", ".dockerignore"])
def test_upload_includes_the_app_and_what_cloud_build_needs(path):
    assert not is_ignored(path, ignore_patterns(".gcloudignore"))


@pytest.mark.parametrize("path", APP_FILES)
def test_image_includes_the_app_and_the_shared_package(path):
    assert not is_ignored(path, ignore_patterns(".dockerignore"))


@pytest.mark.parametrize("ignore_file", [".gcloudignore", ".dockerignore"])
@pytest.mark.parametrize("path", PRIVATE_FILES + ["tests/test_users.py", "__pycache__/server.cpython-312.pyc"])
def test_local_data_secrets_and_tests_stay_out(ignore_file, path):
    assert is_ignored(path, ignore_patterns(ignore_file))


def test_container_starts_the_app_factory():
    assert '"server:create_app()"' in (SERVER_DIR / "Dockerfile").read_text()
