def test_overview_is_admin_only(client, repo, sign_in):
    repo.add_user("ann", "Ann")
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/admin/overview", headers=sign_in("ann")).status_code == 403


def test_overview_combines_users_gifts_matches_and_photo_counts(client, repo, admin_headers):
    repo.add_user("ann", "Ann", "Lee", profilePicturePath="avatars/ann/p.webp")
    repo.add_user("bo", "Bo", "Ray")
    repo.set_gifts("ann", [{"name": "Socks"}])
    repo.assignments[2026] = {"bo": "ann", "ann": "gone"}
    repo.seasons[2026] = {"generation": 2, "status": "matched"}
    repo.add_ready_photo("ann", 2026)
    repo.create_photo("ann", 2026, "image/jpeg", 1)  # pending counts too
    repo.add_ready_photo("ann", 2025)  # other seasons don't

    overview = client.get("/api/admin/overview", headers=admin_headers).json
    assert overview["season"] == 2026 and overview["generation"] == 2
    users = {user["id"]: user for user in overview["users"]}
    assert set(users) == {"admin", "ann", "bo"}

    assert users["ann"]["gifts"][0]["name"] == "Socks"
    assert users["ann"]["photo_count"] == 2 and users["bo"]["photo_count"] == 0
    assert users["ann"]["profile_picture_url"].endswith("avatars/ann/p.webp")
    assert users["bo"]["assigned_to"] == {"id": "ann", "first_name": "Ann", "last_name": "Lee"}
    # A match pointing at a deleted user shows as no match
    assert users["ann"]["assigned_to"] is None and users["admin"]["assigned_to"] is None


def test_overview_never_includes_questions(client, repo, admin_headers):
    repo.create_question("secret")
    assert "secret" not in client.get("/api/admin/overview", headers=admin_headers).get_data(as_text=True)
