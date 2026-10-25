import pytest


@pytest.fixture
def ann(repo, sign_in):
    repo.add_user("ann", "Ann")
    return sign_in("ann")


def test_gifts_require_sign_in(client):
    assert client.get("/api/me/gifts").status_code == 401
    assert client.put("/api/me/gifts", json={"gifts": []}).status_code == 401


def test_old_per_user_gift_routes_are_gone(client, ann):
    assert client.get("/api/users/ann/gifts", headers=ann).status_code == 404


def test_gifts_without_profile_are_404(client, sign_in):
    headers = sign_in("ghost")
    assert client.get("/api/me/gifts", headers=headers).status_code == 404
    assert client.put("/api/me/gifts", headers=headers, json={"gifts": []}).status_code == 404


def test_replace_and_read_gifts(client, repo, ann):
    response = client.put("/api/me/gifts", headers=ann, json={"gifts": [
        {"name": " Socks ", "url": "https://shop.example/socks", "notes": " wool "},
        {"name": "Mug", "url": "", "notes": ""},
    ]})
    expected = [
        {"id": 0, "user_id": "ann", "name": "Socks", "url": "https://shop.example/socks", "notes": "wool", "position": 0},
        {"id": 1, "user_id": "ann", "name": "Mug", "url": None, "notes": None, "position": 1},
    ]
    assert response.status_code == 200 and response.json == expected
    assert client.get("/api/me/gifts", headers=ann).json == expected


def test_put_replaces_the_whole_list(client, repo, ann):
    client.put("/api/me/gifts", headers=ann, json={"gifts": [{"name": "A"}, {"name": "B"}]})
    client.put("/api/me/gifts", headers=ann, json={"gifts": [{"name": "C"}]})
    assert [gift["name"] for gift in repo.users["ann"]["gifts"]] == ["C"]


def test_up_to_four_gifts(client, ann):
    assert client.put("/api/me/gifts", headers=ann, json={"gifts": [{"name": "x"}] * 4}).status_code == 200
    assert client.put("/api/me/gifts", headers=ann, json={"gifts": [{"name": "x"}] * 5}).status_code == 400


@pytest.mark.parametrize("body", [{}, {"gifts": "socks"}, {"gifts": [{"name": " "}]}, {"gifts": [None]}])
def test_rejects_malformed_lists_and_missing_names(client, ann, body):
    assert client.put("/api/me/gifts", headers=ann, json=body).status_code == 400


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "JavaScript:alert(1)", "data:text/html,<script>", "ftp://files.example",
    "https://", "shop.example/socks",
])
def test_only_http_and_https_links_are_allowed(client, repo, ann, url):
    response = client.put("/api/me/gifts", headers=ann, json={"gifts": [{"name": "Bad", "url": url}]})
    assert response.status_code == 400
    assert repo.users["ann"]["gifts"] == []


@pytest.mark.parametrize("url", ["http://shop.example", "https://shop.example/a?b=c", "HTTPS://SHOP.EXAMPLE"])
def test_web_links_are_accepted(client, ann, url):
    assert client.put("/api/me/gifts", headers=ann, json={"gifts": [{"name": "Ok", "url": url}]}).status_code == 200
