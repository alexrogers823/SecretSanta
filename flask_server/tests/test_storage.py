"""storage.py against fakes of google-auth and google-cloud-storage, so no cloud calls are made.

Whether Google accepts the signatures can only be checked against the real bucket (Phase 5).
"""
import os
import threading
import time
from datetime import timedelta
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import NotFound

import storage
from server import create_app


class FakeBlob:
    def __init__(self, bucket, path):
        self.bucket, self.name = bucket, path

    def generate_signed_url(self, **kwargs):
        time.sleep(0.005)  # like the IAM API call, so signatures overlap
        self.bucket.signed.append((self.name, kwargs, threading.current_thread().name))
        return f"https://signed.example/{self.name}?method={kwargs['method']}"

    def delete(self):
        if self.name in self.bucket.missing:
            raise NotFound("gone")
        self.bucket.deleted.append(self.name)


class FakeBucket:
    def __init__(self):
        self.signed, self.deleted, self.missing = [], [], set()
        self.objects = []

    def blob(self, path):
        return FakeBlob(self, path)

    def list_blobs(self, prefix):
        return [FakeBlob(self, name) for name in self.objects if name.startswith(prefix)]


@pytest.fixture
def gcs_app(repo):
    return create_app({"TESTING": True, "STORAGE_MODE": "gcs", "ALLOWED_ORIGINS": []})


@pytest.fixture
def bucket(gcs_app, monkeypatch):
    fake = FakeBucket()
    credentials = SimpleNamespace(service_account_email="api@example.iam", token="access-token")
    monkeypatch.setattr(storage, "_signing_credentials", lambda: credentials)
    monkeypatch.setattr(storage, "_bucket", lambda name: fake)
    with gcs_app.app_context():
        yield fake


def test_upload_url_is_a_v4_put_bound_to_type_and_size(bucket):
    url, headers = storage.upload_url("photos", "uploads/2026/u/p", "image/jpeg", 1000)
    assert headers == {"Content-Type": "image/jpeg", "x-goog-content-length-range": "0,1000"}
    [(path, kwargs, _)] = bucket.signed
    assert path == "uploads/2026/u/p" and url.startswith("https://signed.example/")
    assert kwargs == {
        "version": "v4",
        "method": "PUT",
        "expiration": timedelta(minutes=15),
        "content_type": "image/jpeg",
        "headers": {"x-goog-content-length-range": "0,1000"},
        # Signed by the IAM API as the service account, since Cloud Run has no key file
        "service_account_email": "api@example.iam",
        "access_token": "access-token",
    }


def test_view_url_is_a_one_hour_get(bucket):
    storage.view_url("photos", "thumbs/x.webp")
    [(_, kwargs, _)] = bucket.signed
    assert kwargs["method"] == "GET" and kwargs["expiration"] == timedelta(hours=1)
    assert "content_type" not in kwargs


def test_view_urls_signs_in_parallel_and_keeps_order(bucket):
    paths = [f"thumbs/{n}.webp" for n in range(40)]
    urls = storage.view_urls("photos", paths)
    assert urls == [f"https://signed.example/{path}?method=GET" for path in paths]
    assert len({thread for _, _, thread in bucket.signed}) > 1


def test_delete_objects_skips_empty_paths_and_missing_objects(bucket):
    bucket.missing.add("gone")
    storage.delete_objects("photos", ["a", None, "gone", "", "b"])
    assert bucket.deleted == ["a", "b"]


def test_delete_prefix_deletes_only_that_prefix(bucket):
    bucket.objects = ["avatars/u1/a.webp", "avatars/u1/b.webp", "avatars/u2/c.webp"]
    storage.delete_prefix("pictures", "avatars/u1/")
    assert bucket.deleted == ["avatars/u1/a.webp", "avatars/u1/b.webp"]


# Credentials

class FakeCredentials:
    def __init__(self, email=None):
        self.valid = False
        self.refreshes = 0
        self.token = None
        if email:
            self.service_account_email = email

    def refresh(self, request):
        self.refreshes += 1
        self.valid, self.token = True, f"token-{self.refreshes}"


def test_user_credentials_cannot_sign_and_explain_what_to_do(gcs_app, monkeypatch):
    monkeypatch.setattr(storage.google.auth, "default", lambda scopes: (FakeCredentials(), "project"))
    with gcs_app.app_context(), pytest.raises(RuntimeError, match="STORAGE_MODE=local"):
        storage.view_url("photos", "x")


def test_service_account_credentials_are_loaded_once_and_refreshed_when_expired(gcs_app, monkeypatch):
    credentials = FakeCredentials("api@example.iam")
    loads = []
    monkeypatch.setattr(storage.google.auth, "default", lambda scopes: loads.append(scopes) or (credentials, "p"))
    assert storage._signing_credentials() is credentials and credentials.refreshes == 1
    assert storage._signing_credentials() is credentials and credentials.refreshes == 1
    credentials.valid = False
    storage._signing_credentials()
    assert credentials.refreshes == 2 and len(loads) == 1


# Local mode

def test_local_file_refuses_paths_outside_its_bucket_folder(app):
    with app.app_context():
        assert storage.local_file("photos", "uploads/a/b").endswith(os.path.join("dev_storage", "photos", "uploads", "a", "b"))
        assert storage.local_file("photos", "../../server.py") is None
        assert storage.local_file("photos", "/etc/passwd") is None


def test_local_urls_point_at_the_dev_storage_routes(app):
    with app.test_request_context():
        url, headers = storage.upload_url("secret-santa-photos", "uploads/2026/u/p", "image/png", 10)
        assert url == "http://localhost/api/dev-storage/secret-santa-photos/uploads/2026/u/p"
        assert headers["x-goog-content-length-range"] == "0,10"
        assert storage.view_urls("secret-santa-photos", ["a", "b"]) == [
            "http://localhost/api/dev-storage/secret-santa-photos/a",
            "http://localhost/api/dev-storage/secret-santa-photos/b",
        ]


def test_local_deletes_tolerate_missing_files(app):
    with app.app_context():
        storage.delete_objects("photos", ["never/existed"])
        storage.delete_prefix("photos", "never/")
