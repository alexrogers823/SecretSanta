import inspect
import re

import pytest

import repository
from routes import questions as question_routes


@pytest.fixture
def ann(repo, sign_in):
    repo.add_user("ann", "Ann", email="ann@example.com")
    return sign_in("ann", "ann@example.com")


def test_asking_requires_sign_in(client, repo):
    assert client.post("/api/questions", json={"text": "hi"}).status_code == 401
    assert repo.questions == {}


def test_question_is_stored_without_any_trace_of_the_asker(client, repo, ann):
    response = client.post("/api/questions", headers=ann, json={"text": "  Is there a price limit?  "})
    assert response.status_code == 201 and response.json == {"sent": True}
    [stored] = repo.questions.values()
    assert set(stored) == {"text", "createdAt", "answered"}
    assert stored["text"] == "Is there a price limit?"
    assert "ann" not in repr(stored)


def test_response_does_not_echo_an_id_that_could_be_linked_back(client, ann):
    assert client.post("/api/questions", headers=ann, json={"text": "Q"}).json == {"sent": True}


def test_create_question_accepts_no_asker():
    assert list(inspect.signature(repository.create_question).parameters) == ["text"]


def test_route_never_touches_the_signed_in_identity():
    source = inspect.getsource(question_routes)
    assert "g.uid" not in source.replace("g.uid/g.email", "")
    assert "g.email" not in source.replace("g.uid/g.email", "")
    assert not re.search(r"\blogging\b|\blogger\b|(?<![\w.])print\(", source)


@pytest.mark.parametrize("body", [{}, {"text": ""}, {"text": "   "}, {"text": "x" * 2001}])
def test_rejects_empty_and_overlong_questions(client, repo, ann, body):
    assert client.post("/api/questions", headers=ann, json=body).status_code == 400
    assert repo.questions == {}


def test_admin_lists_questions_newest_first(client, ann, admin_headers):
    client.post("/api/questions", headers=ann, json={"text": "First"})
    client.post("/api/questions", headers=ann, json={"text": "Second"})
    questions = client.get("/api/questions", headers=admin_headers).json
    assert [q["text"] for q in questions] == ["Second", "First"]
    assert all(set(q) == {"id", "text", "created_at", "answered"} for q in questions)


def test_only_admin_can_list_questions(client, ann):
    assert client.get("/api/questions").status_code == 401
    assert client.get("/api/questions", headers=ann).status_code == 403
