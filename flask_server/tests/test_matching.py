import pytest

from shared import matching
from shared.matching import NoValidMatchError, generate_derangement


def _is_single_cycle(mapping):
    start = next(iter(mapping))
    seen, current = set(), start
    while current not in seen:
        seen.add(current)
        current = mapping[current]
    return current == start and seen == set(mapping)


@pytest.mark.parametrize("ids", [["a", "b"], ["a", "b", "c"], list("abcdefghij")])
def test_everyone_gives_and_receives_once_in_one_cycle(ids):
    for _ in range(50):
        mapping = generate_derangement(ids)
        assert set(mapping) == set(ids)
        assert sorted(mapping.values()) == sorted(ids)
        assert all(giver != receiver for giver, receiver in mapping.items())
        assert _is_single_cycle(mapping)


@pytest.mark.parametrize("ids", [[], ["solo"]])
def test_needs_at_least_two_people(ids):
    with pytest.raises(ValueError):
        generate_derangement(ids)


def test_excluded_pairs_never_appear():
    exclusions = {("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")}
    for _ in range(200):
        mapping = generate_derangement(["a", "b", "c", "d"], exclusions)
        assert not exclusions & set(mapping.items())


def test_three_people_avoiding_last_years_cycle_get_the_reverse_cycle():
    last_year = {("a", "b"), ("b", "c"), ("c", "a")}
    for _ in range(20):
        assert generate_derangement(["a", "b", "c"], last_year) == {"a": "c", "c": "b", "b": "a"}


def test_two_people_cannot_avoid_last_year():
    with pytest.raises(NoValidMatchError):
        generate_derangement(["a", "b"], {("a", "b")})


def test_gives_up_after_max_attempts(monkeypatch):
    shuffles = []
    monkeypatch.setattr(matching, "MAX_ATTEMPTS", 7)
    monkeypatch.setattr(matching._random, "shuffle", lambda items: shuffles.append(list(items)))
    with pytest.raises(NoValidMatchError):
        # Without shuffling the draw is always a->b->c->a, which is excluded
        generate_derangement(["a", "b", "c"], {("a", "b")})
    assert len(shuffles) == 7


def test_exclusions_for_people_not_in_the_draw_are_ignored():
    mapping = generate_derangement(["a", "b"], {("x", "y")})
    assert mapping == {"a": "b", "b": "a"}


def test_uses_a_cryptographically_strong_random_source():
    import random
    assert isinstance(matching._random, random.SystemRandom)
