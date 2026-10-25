import os

import pytest

from routes import photos as photo_routes

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
MAX = 15 * 1024 * 1024


def jpeg_file(size=len(JPEG)):
    return {"filename": "x.jpg", "content_type": "image/jpeg", "size": size}


@pytest.fixture
def ann(repo, sign_in):
    repo.add_user("ann", "Ann")
    return sign_in("ann")


@pytest.fixture
def bo(repo, sign_in):
    repo.add_user("bo", "Bo")
    return sign_in("bo")


def upload(client, upload, body=JPEG, **header_overrides):
    """PUTs to an upload URL the way the browser will, with the headers the API returned."""
    return client.put(upload["upload_url"], data=body, headers={**upload["headers"], **header_overrides})


# POST /api/photos/uploads

def test_uploading_requires_sign_in_and_a_profile(client, sign_in):
    assert client.post("/api/photos/uploads", json={"files": [jpeg_file()]}).status_code == 401
    assert client.post("/api/photos/uploads", headers=sign_in("ghost"), json={"files": [jpeg_file()]}).status_code == 403


def test_upload_request_returns_bound_urls_and_pending_photos(client, repo, ann):
    response = client.post("/api/photos/uploads", headers=ann, json={"files": [
        jpeg_file(), {"filename": "y.png", "content_type": "image/png", "size": 5},
    ]})
    assert response.status_code == 201
    first, second = response.json
    assert set(first) == {"photo_id", "upload_url", "headers"}
    assert first["headers"] == {"Content-Type": "image/jpeg", "x-goog-content-length-range": f"0,{MAX}"}
    assert second["headers"]["Content-Type"] == "image/png"
    assert f"/uploads/2026/ann/{first['photo_id']}" in first["upload_url"]
    assert repo.photos[first["photo_id"]]["status"] == "pending"


@pytest.mark.parametrize("files", [
    [], "x", [jpeg_file()] * 11,
    [{"content_type": "image/gif", "size": 5}],
    [{"content_type": "text/html", "size": 5}],
    [jpeg_file(size=MAX + 1)], [jpeg_file(size=0)], [jpeg_file(size="5")], [jpeg_file(size=True)],
    [None],
])
def test_rejects_bad_upload_requests(client, repo, ann, files):
    assert client.post("/api/photos/uploads", headers=ann, json={"files": files}).status_code == 400
    assert repo.photos == {}


def test_accepts_heic_and_the_size_limit_exactly(client, ann):
    files = [{"content_type": "image/heic", "size": 5}, jpeg_file(size=MAX)]
    assert client.post("/api/photos/uploads", headers=ann, json={"files": files}).status_code == 201


def test_twenty_five_photos_per_season_counting_pending(client, repo, ann):
    for _ in range(2):
        assert client.post("/api/photos/uploads", headers=ann, json={"files": [jpeg_file()] * 10}).status_code == 201
    response = client.post("/api/photos/uploads", headers=ann, json={"files": [jpeg_file()] * 6})
    assert response.status_code == 400 and "5 left" in response.json["error"]
    assert client.post("/api/photos/uploads", headers=ann, json={"files": [jpeg_file()] * 5}).status_code == 201


def test_rejected_and_other_season_photos_dont_count(client, repo, ann):
    for _ in range(25):
        repo.add_ready_photo("ann", 2025)
    rejected = repo.create_photo("ann", 2026, "image/jpeg", 1)
    repo.photos[rejected["id"]]["status"] = "rejected"
    assert client.post("/api/photos/uploads", headers=ann, json={"files": [jpeg_file()] * 10}).status_code == 201


# Local dev storage, standing in for the bucket and F6

def test_uploaded_photo_becomes_ready_and_viewable(client, repo, ann):
    [request] = client.post("/api/photos/uploads", headers=ann, json={"files": [jpeg_file()]}).json
    assert upload(client, request).status_code == 200
    photo = repo.photos[request["photo_id"]]
    assert photo["status"] == "ready"
    assert photo["displayPath"] == f"display/2026/ann/{request['photo_id']}.webp"

    [listed] = client.get("/api/photos").json["photos"]
    image = client.get(listed["display_url"])
    assert image.status_code == 200 and image.mimetype == "image/jpeg" and image.data == JPEG


def test_upload_larger_than_its_url_allows_is_rejected(client, repo, ann):
    [request] = client.post("/api/photos/uploads", headers=ann, json={"files": [jpeg_file()]}).json
    assert upload(client, request, body=b"x" * 11, **{"x-goog-content-length-range": "0,10"}).status_code == 400
    assert repo.photos[request["photo_id"]]["status"] == "pending"


def test_upload_for_unknown_photo_is_discarded(client, app, repo, ann):
    url = "/api/dev-storage/secret-santa-photos/uploads/2026/ann/made-up"
    headers = {"Content-Type": "image/jpeg", "x-goog-content-length-range": f"0,{MAX}"}
    assert client.put(url, data=JPEG, headers=headers).status_code == 200
    assert not os.path.exists(os.path.join(app.instance_path, "dev_storage", "secret-santa-photos", "uploads", "2026", "ann", "made-up"))


@pytest.mark.parametrize("url", [
    "/api/dev-storage/secret-santa-photos/display/2026/ann/x.webp",  # only uploads/ is writable
    "/api/dev-storage/some-other-bucket/uploads/x",
])
def test_dev_storage_only_accepts_uploads_to_known_buckets(client, url):
    headers = {"Content-Type": "image/jpeg", "x-goog-content-length-range": f"0,{MAX}"}
    assert client.put(url, data=JPEG, headers=headers).status_code in (403, 404)


# GET /api/photos

def test_gallery_is_public_and_hides_owners(client, repo, ann):
    repo.add_ready_photo("ann", 2026)
    response = client.get("/api/photos")
    assert response.status_code == 200
    assert response.json["season"] == 2026 and response.json["seasons"] == [2026]
    [photo] = response.json["photos"]
    assert set(photo) == {"id", "thumb_url", "display_url", "created_at"}


def test_gallery_shows_only_ready_photos_newest_first(client, repo, ann):
    older = repo.add_ready_photo("ann", 2026)
    newer = repo.add_ready_photo("ann", 2026)
    repo.create_photo("ann", 2026, "image/jpeg", 1)
    assert [p["id"] for p in client.get("/api/photos").json["photos"]] == [newer["id"], older["id"]]


def test_members_see_owner_names_and_what_they_can_delete(client, repo, ann, bo, admin_headers):
    repo.add_ready_photo("ann", 2026)
    [as_bo] = client.get("/api/photos", headers=bo).json["photos"]
    assert as_bo["owner_first_name"] == "Ann" and as_bo["can_delete"] is False
    assert "owner_uid" not in as_bo
    assert client.get("/api/photos", headers=ann).json["photos"][0]["can_delete"] is True
    assert client.get("/api/photos", headers=admin_headers).json["photos"][0]["can_delete"] is True


def test_past_seasons_stay_available(client, repo, ann):
    repo.add_ready_photo("ann", 2024)
    response = client.get("/api/photos?season=2024").json
    assert response["season"] == 2024 and len(response["photos"]) == 1
    assert response["seasons"] == [2026, 2024]  # the current season is always listed


def test_visitors_get_a_cached_list_and_members_refresh_it(client, repo, ann):
    repo.add_ready_photo("ann", 2026)
    assert len(client.get("/api/photos").json["photos"]) == 1
    repo.add_ready_photo("ann", 2026)
    assert len(client.get("/api/photos").json["photos"]) == 1  # cached
    assert len(client.get("/api/photos", headers=ann).json["photos"]) == 2  # members always fresh
    assert len(client.get("/api/photos").json["photos"]) == 2  # and that refreshed the cache


def test_cache_expires(client, repo, ann, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(photo_routes.time, "monotonic", lambda: clock[0])
    client.get("/api/photos")
    repo.add_ready_photo("ann", 2026)
    clock[0] += photo_routes.CACHE_SECONDS - 1
    assert client.get("/api/photos").json["photos"] == []
    clock[0] += 2
    assert len(client.get("/api/photos").json["photos"]) == 1


def test_visitors_get_signed_urls_built_once_per_cache_period(client, repo, ann, monkeypatch):
    import photo_storage
    calls = []
    monkeypatch.setattr(photo_storage, "view_urls", lambda paths: calls.append(paths) or [f"signed:{p}" for p in paths])
    photo = repo.add_ready_photo("ann", 2026)
    for _ in range(3):
        [listed] = client.get("/api/photos").json["photos"]
    assert len(calls) == 1
    assert listed["thumb_url"] == f"signed:{photo['thumbPath']}"
    assert listed["display_url"] == f"signed:{photo['displayPath']}"


# DELETE /api/photos/<id>

def test_owner_and_admin_can_delete_others_cannot(client, repo, ann, bo, admin_headers):
    first = repo.add_ready_photo("ann", 2026)
    second = repo.add_ready_photo("ann", 2026)
    assert client.delete(f"/api/photos/{first['id']}").status_code == 401
    assert client.delete(f"/api/photos/{first['id']}", headers=bo).status_code == 403
    assert client.delete(f"/api/photos/{first['id']}", headers=ann).status_code == 204
    assert client.delete(f"/api/photos/{second['id']}", headers=admin_headers).status_code == 204
    assert repo.photos == {}
    assert client.delete("/api/photos/missing", headers=admin_headers).status_code == 404


def test_delete_removes_files_and_clears_the_cache(client, app, repo, ann):
    [request] = client.post("/api/photos/uploads", headers=ann, json={"files": [jpeg_file()]}).json
    upload(client, request)
    photo = repo.get_photo(request["photo_id"])
    files = [os.path.join(app.instance_path, "dev_storage", "secret-santa-photos", photo[key]) for key in ("displayPath", "thumbPath")]
    assert all(os.path.exists(file) for file in files)
    assert len(client.get("/api/photos").json["photos"]) == 1

    client.delete(f"/api/photos/{photo['id']}", headers=ann)
    assert not any(os.path.exists(file) for file in files)
    assert client.get("/api/photos").json["photos"] == []
