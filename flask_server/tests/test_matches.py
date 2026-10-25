from datetime import datetime, timedelta, timezone

import pytest

PAST = datetime.now(timezone.utc) - timedelta(minutes=1)
FUTURE = datetime.now(timezone.utc) + timedelta(days=30)


@pytest.fixture
def people(repo, sign_in):
    """Ann, Bo and Cy, all signed in. Returns their headers by uid."""
    for uid, name in (("ann", "Ann"), ("bo", "Bo"), ("cy", "Cy")):
        repo.add_user(uid, name)
    return {uid: sign_in(uid) for uid in ("ann", "bo", "cy")}


def test_public_generate_and_per_user_routes_are_gone(client, people, admin_headers):
    assert client.post("/api/matches/generate", headers=admin_headers).status_code == 404
    assert client.get("/api/matches/ann", headers=admin_headers).status_code == 404


# GET /api/matches/me

def test_my_match_requires_sign_in(client):
    assert client.get("/api/matches/me").status_code == 401


def test_my_match_is_hidden_before_reveal_even_when_drawn(client, repo, people):
    repo.season_config = {"year": 2026, "revealAt": FUTURE}
    repo.assignments[2026] = {"ann": "bo"}
    assert client.get("/api/matches/me", headers=people["ann"]).json == {
        "revealed": False, "reveal_at": FUTURE.isoformat(),
    }


def test_my_match_is_hidden_after_reveal_until_drawn(client, repo, people):
    repo.season_config = {"year": 2026, "revealAt": PAST}
    assert client.get("/api/matches/me", headers=people["ann"]).json["revealed"] is False


def test_my_match_after_reveal_shows_receiver_and_gifts(client, repo, people):
    repo.season_config = {"year": 2026, "revealAt": PAST}
    repo.assignments[2026] = {"ann": "bo"}
    repo.set_gifts("bo", [{"name": "Socks", "url": "https://s.example"}])
    response = client.get("/api/matches/me", headers=people["ann"]).json
    assert response["revealed"] is True
    assert response["receiver"] == {
        "first_name": "Bo", "last_name": "Tester", "address": "1 Elf Rd", "profile_picture_url": None,
    }
    assert [gift["name"] for gift in response["gifts"]] == ["Socks"]


def test_my_match_never_includes_receivers_email(client, repo, people):
    repo.season_config = {"year": 2026, "revealAt": PAST}
    repo.assignments[2026] = {"ann": "bo"}
    assert "email" not in client.get("/api/matches/me", headers=people["ann"]).json["receiver"]


def test_receivers_picture_is_shown_only_after_reveal(client, repo, people):
    repo.users["bo"]["profilePicturePath"] = "avatars/bo/p.webp"
    repo.assignments[2026] = {"ann": "bo"}
    repo.season_config = {"year": 2026, "revealAt": FUTURE}
    assert "receiver" not in client.get("/api/matches/me", headers=people["ann"]).json
    repo.season_config = {"year": 2026, "revealAt": PAST}
    url = client.get("/api/matches/me", headers=people["ann"]).json["receiver"]["profile_picture_url"]
    assert url.endswith("avatars/bo/p.webp")


def test_my_match_when_receiver_was_deleted(client, repo, people):
    repo.season_config = {"year": 2026, "revealAt": PAST}
    repo.assignments[2026] = {"ann": "gone"}
    response = client.get("/api/matches/me", headers=people["ann"]).json
    assert response["revealed"] is True and response["receiver"] is None and response["gifts"] == []


# Admin routes

def test_listing_and_regenerating_are_admin_only(client, people):
    assert client.get("/api/matches", headers=people["ann"]).status_code == 403
    assert client.post("/api/matches/regenerate", headers=people["ann"]).status_code == 403


def test_admin_list_shows_everyones_match(client, repo, people, admin_headers):
    repo.assignments[2026] = {"ann": "bo", "bo": "ann"}
    matches = {m["user_id"]: m["assigned_to"] for m in client.get("/api/matches", headers=admin_headers).json}
    assert matches["ann"]["id"] == "bo" and matches["bo"]["id"] == "ann"
    assert matches["cy"] is None and matches["admin"] is None


def test_regenerate_draws_everyone_and_counts_generations(client, repo, people, admin_headers):
    for generation in (1, 2):
        response = client.post("/api/matches/regenerate", headers=admin_headers)
        assert response.status_code == 200
        mapping = repo.assignments[2026]
        assert set(mapping) == {"ann", "bo", "cy", "admin"}
        assert sorted(mapping.values()) == sorted(mapping)
        assert repo.seasons[2026] == {"generation": generation, "status": "matched"}


def test_regenerate_replaces_rather_than_overwrites(client, repo, people, admin_headers, monkeypatch):
    """The re-email trigger only fires on newly created assignments, so they must be deleted first."""
    import repository
    calls = []
    for name in ("delete_assignments", "write_assignments"):
        original = getattr(repository, name)
        monkeypatch.setattr(repository, name, lambda *args, _name=name, _original=original: (calls.append(_name), _original(*args))[1])
    client.post("/api/matches/regenerate", headers=admin_headers)
    assert calls == ["delete_assignments", "write_assignments"]


def test_regenerate_avoids_last_years_pairs_only(client, repo, sign_in, admin_headers):
    repo.users.pop("admin")  # just Ann, Bo and Cy
    for uid in ("ann", "bo", "cy"):
        repo.add_user(uid, uid.title())
    repo.assignments[2025] = {"ann": "bo", "bo": "cy", "cy": "ann"}
    # 2024's pairs are the only remaining cycle, so they must be allowed
    repo.assignments[2024] = {"ann": "cy", "cy": "bo", "bo": "ann"}
    for _ in range(10):
        assert client.post("/api/matches/regenerate", headers=admin_headers).status_code == 200
        assert repo.assignments[2026] == {"ann": "cy", "cy": "bo", "bo": "ann"}


def test_regenerate_with_no_valid_draw_changes_nothing(client, repo, sign_in, admin_headers):
    repo.users.pop("admin")
    repo.add_user("ann", "Ann")
    repo.add_user("bo", "Bo")
    repo.assignments[2025] = {"ann": "bo", "bo": "ann"}
    repo.assignments[2026] = {"ann": "bo", "bo": "ann"}
    repo.seasons[2026] = {"generation": 1, "status": "matched"}

    response = client.post("/api/matches/regenerate", headers=admin_headers)
    assert response.status_code == 409 and "ignore_exclusions" in response.json["error"]
    assert repo.assignments[2026] == {"ann": "bo", "bo": "ann"} and repo.get_generation(2026) == 1

    response = client.post("/api/matches/regenerate", headers=admin_headers, json={"ignore_exclusions": True})
    assert response.status_code == 200 and repo.get_generation(2026) == 2


def test_regenerate_needs_two_people(client, repo, admin_headers):
    assert client.post("/api/matches/regenerate", headers=admin_headers).status_code == 400
    assert 2026 not in repo.assignments
