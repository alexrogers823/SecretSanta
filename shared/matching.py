import random

MAX_ATTEMPTS = 1000

_random = random.SystemRandom()


class NoValidMatchError(Exception):
    pass


def generate_derangement(ids, exclusions=frozenset()):
    """Shuffles everyone into one gift-giving cycle, so nobody draws themselves.

    exclusions is a set of (giver, receiver) pairs that must not appear, e.g. last year's pairs.
    """
    if len(ids) < 2:
        raise ValueError("at least 2 ids are required to generate a derangement")

    shuffled = list(ids)
    n = len(shuffled)
    for _ in range(MAX_ATTEMPTS):
        _random.shuffle(shuffled)
        mapping = {shuffled[i]: shuffled[(i + 1) % n] for i in range(n)}
        if not any(pair in exclusions for pair in mapping.items()):
            return mapping
    raise NoValidMatchError("no draw avoids all excluded pairs")
