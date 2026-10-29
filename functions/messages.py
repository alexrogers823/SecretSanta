"""Email wording. Match emails never name the receiver, so an inbox preview can't spoil the surprise."""
import os

from store import EASTERN_STANDARD_TIME

SITE_URL = os.environ.get("SITE_URL", "https://secret-santa-511801.web.app")


def _reveal_text(reveal_at):
    eastern = reveal_at.astimezone(EASTERN_STANDARD_TIME)
    hour = eastern.strftime("%I").lstrip("0")
    minute = eastern.strftime(":%M") if eastern.minute else ""
    return f"{eastern.strftime('%B')} {eastern.day} at {hour}{minute}{eastern.strftime('%p').lower()} Eastern"


def match_ready(first_name, redrawn, revealed, reveal_at):
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    if redrawn:
        subject = "Your Secret Santa match has changed"
        news = "Secret Santa matches were redrawn, so you have a new person this year."
    else:
        subject = "Your Secret Santa match is ready"
        news = "Secret Santa matches have been drawn!"
    when = "Log in to see who you're getting a gift for" if revealed else f"You can see who you're getting a gift for from {_reveal_text(reveal_at)}"
    return subject, f"{greeting}\n\n{news} {when}:\n{SITE_URL}\n\nHappy gifting!\n"


def new_question(text):
    return (
        "New anonymous Secret Santa question",
        f"Someone sent a question (anonymously, so there's no name attached):\n\n{text}\n\n"
        f"See all questions on the admin page: {SITE_URL}/admin\n",
    )


def gift_reminder(first_name, reveal_at):
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    return (
        "Add your Secret Santa wish list",
        f"{greeting}\n\nYou haven't added any gifts to your wish list yet. Add a few before matches are revealed "
        f"on {_reveal_text(reveal_at)}, so your Secret Santa knows what you'd like:\n{SITE_URL}\n",
    )


def no_valid_draw(year):
    return (
        f"Secret Santa {year}: matches couldn't be drawn",
        f"Every possible draw for {year} repeats a pair from last year, so no matches were saved. "
        f"Regenerate them from the admin page and choose to allow repeats:\n{SITE_URL}/admin\n",
    )


def not_enough_people(year, count):
    return (
        f"Secret Santa {year}: matches couldn't be drawn",
        f"Only {count} member{'s' if count != 1 else ''} signed up, and at least 2 are needed. "
        f"Once more people join, regenerate matches from the admin page:\n{SITE_URL}/admin\n",
    )
