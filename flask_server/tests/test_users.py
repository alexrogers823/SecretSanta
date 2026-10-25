import os

import pytest
from firebase_admin import auth as firebase_auth

from routes import users as user_routes

PROFILE = {"first_name": "Ann", "last_name": "Lee", "address": "1 Elf Rd"}


@pytest.fixture
def ann(repo, sign_in):
    repo.invites.add("ann@example.com")
    return sign_in("ann", "ann@example.com")


# GET /api/me

def test_me_requires_sign_in(client):
    assert client.get("/api/me").status_code == 401


def test_me_is_404_until_signup_is_finished(client, ann):
    assert client.get("/api/me", headers=ann).status_code == 404


def test_me_returns_profile_with_is_admin(client, repo, ann, admin_headers):
    repo.add_user("ann", "Ann", "Lee", email="ann@example.com")
    assert client.get("/api/me", headers=ann).json == {
        "id": "ann", "first_name": "Ann", "last_name": "Lee", "email": "ann@example.com",
        "address": "1 Elf Rd", "profile_picture_url": None, "is_admin": False,
    }
    assert client.get("/api/me", headers=admin_headers).json["is_admin"] is True


# POST /api/me

def test_signup_creates_profile_with_email_from_sign_in(client, repo, ann):
    response = client.post("/api/me", headers=ann, json={**PROFILE, "first_name": "  Ann ", "email": "spoof@x.com"})
    assert response.status_code == 201
    assert response.json["first_name"] == "Ann" and response.json["email"] == "ann@example.com"
    assert repo.users["ann"]["email"] == "ann@example.com"


def test_signup_requires_an_invite(client, sign_in):
    response = client.post("/api/me", headers=sign_in("eve", "eve@example.com"), json=PROFILE)
    assert response.status_code == 403


def test_signup_invite_check_ignores_case(client, repo, sign_in):
    repo.invites.add("Mixed@Example.com")
    assert client.post("/api/me", headers=sign_in("m", "mixed@example.com"), json=PROFILE).status_code == 201


def test_admin_can_sign_up_without_an_invite(client, sign_in):
    response = client.post("/api/me", headers=sign_in("boss", "admin@example.com"), json=PROFILE)
    assert response.status_code == 201 and response.json["is_admin"] is True


@pytest.mark.parametrize("field", ["first_name", "last_name", "address"])
def test_signup_requires_every_field(client, ann, field):
    response = client.post("/api/me", headers=ann, json={**PROFILE, field: "   "})
    assert response.status_code == 400 and field in response.json["error"]


def test_signup_twice_is_a_conflict(client, ann):
    client.post("/api/me", headers=ann, json=PROFILE)
    assert client.post("/api/me", headers=ann, json=PROFILE).status_code == 409


# PATCH /api/me

@pytest.fixture
def ann_profile(repo, ann):
    repo.add_user("ann", "Ann", "Lee", email="ann@example.com")
    return ann


def test_patch_me_updates_given_fields_only(client, repo, ann_profile):
    response = client.patch("/api/me", headers=ann_profile, json={"address": " 9 Pole Ln "})
    assert response.status_code == 200
    assert response.json["address"] == "9 Pole Ln" and response.json["first_name"] == "Ann"


def test_patch_me_accepts_the_same_email_back(client, ann_profile):
    assert client.patch("/api/me", headers=ann_profile, json={"email": "ANN@example.com"}).status_code == 200


def test_patch_me_cannot_change_email(client, repo, ann_profile):
    assert client.patch("/api/me", headers=ann_profile, json={"email": "new@example.com"}).status_code == 400
    assert repo.users["ann"]["email"] == "ann@example.com"


@pytest.mark.parametrize("field", ["first_name", "last_name", "address"])
def test_patch_me_rejects_blank_values(client, ann_profile, field):
    assert client.patch("/api/me", headers=ann_profile, json={field: ""}).status_code == 400


def test_patch_me_without_profile_is_404(client, ann):
    assert client.patch("/api/me", headers=ann, json={"address": "x"}).status_code == 404


# Admin user routes

@pytest.mark.parametrize("method, path", [
    ("get", "/api/users"), ("get", "/api/users/bo"), ("put", "/api/users/bo"),
    ("patch", "/api/users/bo"), ("delete", "/api/users/bo"),
])
def test_user_routes_are_admin_only(client, repo, ann_profile, method, path):
    repo.add_user("bo", "Bo")
    assert getattr(client, method)(path).status_code == 401
    assert getattr(client, method)(path, headers=ann_profile, json={}).status_code == 403


def test_old_login_lookup_is_gone(client, repo, admin_headers):
    repo.add_user("bo", "Bo", email="bo@example.com")
    # The query string is ignored: it's the admin list, not a lookup
    response = client.get("/api/users?first_name=Bo&email=bo@example.com", headers=admin_headers)
    assert len(response.json) == 2
    assert client.post("/api/users", headers=admin_headers, json={}).status_code == 405


def test_admin_get_and_list(client, repo, admin_headers):
    repo.add_user("bo", "Bo")
    assert {user["id"] for user in client.get("/api/users", headers=admin_headers).json} == {"admin", "bo"}
    assert client.get("/api/users/bo", headers=admin_headers).json["first_name"] == "Bo"
    assert client.get("/api/users/nobody", headers=admin_headers).status_code == 404


def test_admin_put_requires_every_field_and_lowercases_email(client, repo, admin_headers):
    repo.add_user("bo", "Bo")
    body = {"first_name": "Bob", "last_name": "Ray", "email": "BOB@Example.com", "address": "2 Sled St"}
    assert client.put("/api/users/bo", headers=admin_headers, json={**body, "address": ""}).status_code == 400
    response = client.put("/api/users/bo", headers=admin_headers, json=body)
    assert response.status_code == 200 and response.json["email"] == "bob@example.com"
    assert client.put("/api/users/nobody", headers=admin_headers, json={**body, "email": "z@z.com"}).status_code == 404


def test_admin_patch_rejects_blank_email_and_address(client, repo, admin_headers):
    repo.add_user("bo", "Bo")
    assert client.patch("/api/users/bo", headers=admin_headers, json={"email": " "}).status_code == 400
    assert client.patch("/api/users/bo", headers=admin_headers, json={"address": ""}).status_code == 400


@pytest.mark.parametrize("method", ["put", "patch"])
def test_admin_cannot_give_two_users_the_same_email(client, repo, admin_headers, method):
    repo.add_user("bo", "Bo", email="bo@example.com")
    repo.add_user("cy", "Cy", email="cy@example.com")
    body = {"first_name": "Cy", "last_name": "K", "email": "BO@example.com", "address": "3"}
    assert getattr(client, method)("/api/users/cy", headers=admin_headers, json=body).status_code == 409
    # Keeping your own email isn't a conflict
    assert getattr(client, method)("/api/users/bo", headers=admin_headers, json={**body, "first_name": "Bo"}).status_code == 200


# DELETE /api/users/<id>

@pytest.fixture
def deleted_auth_users(monkeypatch):
    deleted = []

    def delete_user(uid):
        if uid == "no-auth-account":
            raise firebase_auth.UserNotFoundError("missing")
        deleted.append(uid)
    monkeypatch.setattr(user_routes.auth, "delete_user", delete_user)
    return deleted


def test_delete_user_removes_profile_photos_pictures_and_sign_in(client, repo, app, admin_headers, deleted_auth_users):
    repo.add_user("bo", "Bo", profilePicturePath="avatars/bo/p1.webp")
    photo = repo.add_ready_photo("bo", 2026)
    repo.add_ready_photo("admin", 2026)
    files = []
    for bucket, path in (("secret-santa-profile-photos", "avatars/bo/p1.webp"),
                         ("secret-santa-photos", photo["displayPath"]),
                         ("secret-santa-photos", photo["thumbPath"])):
        file = os.path.join(app.instance_path, "dev_storage", bucket, path)
        files.append(file)
        os.makedirs(os.path.dirname(file), exist_ok=True)
        open(file, "wb").close()

    response = client.delete("/api/users/bo", headers=admin_headers)
    assert response.status_code == 200 and response.json == {"deleted": "bo"}
    assert "bo" not in repo.users
    assert [p["ownerUid"] for p in repo.photos.values()] == ["admin"]
    assert deleted_auth_users == ["bo"]
    assert not any(os.path.exists(file) for file in files)


def test_delete_user_after_matches_warns_and_removes_their_assignment(client, repo, admin_headers, deleted_auth_users):
    repo.add_user("bo", "Bo")
    repo.assignments[2026] = {"bo": "admin", "admin": "bo"}
    response = client.delete("/api/users/bo", headers=admin_headers)
    assert "warning" in response.json
    assert repo.assignments[2026] == {"admin": "bo"}


def test_delete_user_without_auth_account_still_succeeds(client, repo, admin_headers, deleted_auth_users):
    repo.add_user("no-auth-account", "Old")
    assert client.delete("/api/users/no-auth-account", headers=admin_headers).status_code == 200


def test_delete_missing_user_is_404(client, admin_headers, deleted_auth_users):
    assert client.delete("/api/users/nobody", headers=admin_headers).status_code == 404
    assert deleted_auth_users == []
