from datetime import datetime, timedelta, timezone

import repository

# Nov 25 is always after daylight saving ends, so Eastern time is a fixed UTC-5 that day
EASTERN_STANDARD_TIME = timezone(timedelta(hours=-5))


def current_season():
    """Returns (year, reveal_at) from config/season.

    Until config/season is seeded (Phase 5), falls back to this calendar year and
    Nov 25 at 12pm Eastern, the same date the client shows.
    """
    config = repository.get_season_config() or {}
    year = config.get("year") or datetime.now(EASTERN_STANDARD_TIME).year
    reveal_at = config.get("revealAt") or datetime(year, 11, 25, 12, tzinfo=EASTERN_STANDARD_TIME)
    return year, reveal_at


def is_revealed(reveal_at):
    return datetime.now(timezone.utc) >= reveal_at
