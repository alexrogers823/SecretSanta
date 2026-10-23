import random


def generate_derangement(ids):
    if len(ids) < 2:
        raise ValueError("at least 2 ids are required to generate a derangement")

    shuffled = list(ids)
    random.shuffle(shuffled)
    n = len(shuffled)
    return {shuffled[i]: shuffled[(i + 1) % n] for i in range(n)}
