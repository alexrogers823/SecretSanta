from datetime import datetime, timedelta, timezone

import season


def test_reads_year_and_reveal_time_from_config(repo):
    reveal_at = datetime(2030, 11, 25, 17, tzinfo=timezone.utc)
    repo.season_config = {"year": 2030, "revealAt": reveal_at}
    assert season.current_season() == (2030, reveal_at)


def test_falls_back_to_this_year_and_nov_25_noon_eastern(repo):
    repo.season_config = None
    year, reveal_at = season.current_season()
    assert year == datetime.now(season.EASTERN_STANDARD_TIME).year
    assert reveal_at == datetime(year, 11, 25, 17, tzinfo=timezone.utc)  # 12pm EST


def test_config_year_without_reveal_time_uses_that_years_nov_25(repo):
    repo.season_config = {"year": 2031}
    assert season.current_season()[1] == datetime(2031, 11, 25, 12, tzinfo=season.EASTERN_STANDARD_TIME)


def test_is_revealed():
    now = datetime.now(timezone.utc)
    assert season.is_revealed(now - timedelta(seconds=1))
    assert not season.is_revealed(now + timedelta(minutes=1))
