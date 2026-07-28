from datetime import date, time

from bot.text_parsing import find_date, find_time


def test_find_date_with_year():
    assert find_date("28 июля 2026 в 19:00", date(2026, 1, 1)) == date(2026, 7, 28)


def test_find_date_without_year_uses_current_year():
    assert find_date("5 августа, начало в 19:30", date(2026, 7, 28)) == date(2026, 8, 5)


def test_find_date_rolls_to_next_year_when_month_already_passed():
    # "10 января" mentioned while today is late 2026 December should mean next January.
    assert find_date("10 января, суббота", date(2026, 12, 20)) == date(2027, 1, 10)


def test_find_date_returns_none_without_a_match():
    assert find_date("никакой даты тут нет", date(2026, 7, 28)) is None


def test_find_time():
    assert find_time("Начало в 19:00, бар «Огни»") == time(19, 0)


def test_find_time_returns_none_without_a_match():
    assert find_time("расписание на неделю") is None
