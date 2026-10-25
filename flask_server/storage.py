import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import google.auth
from flask import current_app, url_for
from google.api_core.exceptions import NotFound
from google.auth.transport.requests import Request
from google.cloud import storage as gcs
from werkzeug.security import safe_join

UPLOAD_URL_LIFETIME = timedelta(minutes=15)
VIEW_URL_LIFETIME = timedelta(hours=1)
SIGNING_THREADS = 16

_lock = threading.Lock()
_credentials = None
_client = None


def is_local():
    """STORAGE_MODE=local keeps files on disk under instance/dev_storage, for development."""
    return current_app.config["STORAGE_MODE"] == "local"


def local_root(bucket):
    return os.path.join(current_app.instance_path, "dev_storage", bucket)


def local_file(bucket, path):
    # safe_join returns None for paths that try to escape the folder
    return safe_join(local_root(bucket), path)


def _bucket(name):
    global _client
    with _lock:
        if _client is None:
            _client = gcs.Client(project=current_app.config["GOOGLE_CLOUD_PROJECT"])
    return _client.bucket(name)


def _signing_credentials():
    global _credentials
    with _lock:
        if _credentials is None:
            _credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        if not _credentials.valid:
            _credentials.refresh(Request())
        if not getattr(_credentials, "service_account_email", None):
            raise RuntimeError(
                "Signing storage URLs needs service account credentials. Locally, set STORAGE_MODE=local, "
                "or run `gcloud auth application-default login --impersonate-service-account="
                "secret-santa-api@secret-santa-511801.iam.gserviceaccount.com`."
            )
        return _credentials


def _signer(bucket, method, lifetime, **kwargs):
    # Cloud Run has no key file, so the IAM API signs with the service account's token.
    # That's why secret-santa-api needs Token Creator on itself.
    credentials = _signing_credentials()
    gcs_bucket = _bucket(bucket)

    def sign(path):
        return gcs_bucket.blob(path).generate_signed_url(
            version="v4",
            expiration=lifetime,
            method=method,
            service_account_email=credentials.service_account_email,
            access_token=credentials.token,
            **kwargs,
        )
    return sign


def _sign(bucket, path, method, lifetime, **kwargs):
    return _signer(bucket, method, lifetime, **kwargs)(path)


def upload_url(bucket, path, content_type, max_bytes):
    """Returns (url, headers): a PUT URL for one file, and the headers the browser must send with it.

    The URL is bound to the content type and size limit, so the browser can't upload anything else.
    """
    headers = {"Content-Type": content_type, "x-goog-content-length-range": f"0,{max_bytes}"}
    if is_local():
        return url_for("dev_storage.put_object", bucket=bucket, path=path, _external=True), headers
    url = _sign(
        bucket, path, "PUT", UPLOAD_URL_LIFETIME,
        content_type=content_type,
        headers={"x-goog-content-length-range": headers["x-goog-content-length-range"]},
    )
    return url, headers


def view_url(bucket, path):
    if is_local():
        return url_for("dev_storage.get_object", bucket=bucket, path=path, _external=True)
    return _sign(bucket, path, "GET", VIEW_URL_LIFETIME)


def view_urls(bucket, paths):
    """Signs many view URLs. Each signature is an IAM API call on Cloud Run, so they run in parallel."""
    if is_local():
        return [view_url(bucket, path) for path in paths]
    with ThreadPoolExecutor(max_workers=SIGNING_THREADS) as pool:
        return list(pool.map(_signer(bucket, "GET", VIEW_URL_LIFETIME), paths))


def delete_objects(bucket, paths):
    for path in filter(None, paths):
        if is_local():
            file = local_file(bucket, path)
            if file and os.path.isfile(file):
                os.remove(file)
            continue
        try:
            _bucket(bucket).blob(path).delete()
        except NotFound:
            pass


def delete_prefix(bucket, prefix):
    if is_local():
        folder = local_file(bucket, prefix)
        if folder and os.path.isdir(folder):
            shutil.rmtree(folder)
        return
    for blob in _bucket(bucket).list_blobs(prefix=prefix):
        try:
            blob.delete()
        except NotFound:
            pass
