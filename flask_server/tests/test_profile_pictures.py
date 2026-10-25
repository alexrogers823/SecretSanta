import os

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 50
MAX = 5 * 1024 * 1024


@pytest.fixture
def ann(repo, sign_in):
    repo.add_user("ann", "Ann")
    return sign_in("ann")


def request_upload(client, headers, content_type="image/png", size=len(PNG)):
    return client.post("/api/me/profile-picture", headers=headers, json={"content_type": content_type, "size": size})


def put(client, upload, body=PNG):
    return client.put(upload["upload_url"], data=body, headers=upload["headers"])


def test_old_local_disk_routes_are_gone(client, ann):
    for method in ("get", "put", "delete"):
        assert getattr(client, method)("/api/users/ann/profile-picture", headers=ann).status_code in (404, 405)


def test_requires_sign_in_and_a_profile(client, sign_in):
    assert request_upload(client, {}).status_code == 401
    assert request_upload(client, sign_in("ghost")).status_code == 404


@pytest.mark.parametrize("content_type, size", [
    ("image/bmp", 5), ("image/svg+xml", 5), (None, 5),
    ("image/png", MAX + 1), ("image/png", 0), ("image/png", "5"), ("image/png", True),
])
def test_rejects_wrong_type_or_size(client, ann, content_type, size):
    assert request_upload(client, ann, content_type, size).status_code == 400


@pytest.mark.parametrize("content_type", ["image/jpeg", "image/png", "image/gif", "image/webp", "image/heic"])
def test_accepts_supported_types(client, ann, content_type):
    assert request_upload(client, ann, content_type, MAX).status_code == 201


def test_upload_url_is_bound_to_type_and_5mb(client, ann):
    upload = request_upload(client, ann).json
    assert set(upload) == {"picture_id", "upload_url", "headers"}
    assert upload["headers"] == {"Content-Type": "image/png", "x-goog-content-length-range": f"0,{MAX}"}
    assert f"/uploads/ann/{upload['picture_id']}" in upload["upload_url"]


def test_uploaded_picture_becomes_the_avatar(client, repo, ann):
    upload = request_upload(client, ann).json
    assert put(client, upload).status_code == 200
    assert repo.users["ann"]["profilePicturePath"] == f"avatars/ann/{upload['picture_id']}.webp"
    url = client.get("/api/me", headers=ann).json["profile_picture_url"]
    assert client.get(url).data == PNG


def test_replacing_deletes_the_previous_avatar(client, app, repo, ann):
    put(client, request_upload(client, ann).json)
    first = os.path.join(app.instance_path, "dev_storage", "secret-santa-profile-photos", repo.users["ann"]["profilePicturePath"])
    put(client, request_upload(client, ann).json)
    assert not os.path.exists(first)
    assert os.path.exists(os.path.join(app.instance_path, "dev_storage", "secret-santa-profile-photos", repo.users["ann"]["profilePicturePath"]))


def test_removing_the_picture(client, app, repo, ann):
    put(client, request_upload(client, ann).json)
    file = os.path.join(app.instance_path, "dev_storage", "secret-santa-profile-photos", repo.users["ann"]["profilePicturePath"])
    response = client.delete("/api/me/profile-picture", headers=ann)
    assert response.status_code == 200 and response.json["profile_picture_url"] is None
    assert repo.users["ann"]["profilePicturePath"] is None and not os.path.exists(file)


def test_who_can_see_a_profile_picture(client, repo, ann, sign_in, admin_headers):
    """The owner and the admin; the giver only after the reveal (tested in test_matches)."""
    repo.users["ann"]["profilePicturePath"] = "avatars/ann/p.webp"
    repo.add_user("bo", "Bo")
    bo = sign_in("bo")
    assert client.get("/api/me", headers=ann).json["profile_picture_url"]
    assert client.get("/api/users/ann", headers=admin_headers).json["profile_picture_url"]
    assert client.get("/api/users/ann", headers=bo).status_code == 403
    repo.assignments[2026] = {"bo": "ann"}
    for match in client.get("/api/matches", headers=admin_headers).json:
        if match["assigned_to"]:
            assert match["assigned_to"]["profile_picture_url"] is None
