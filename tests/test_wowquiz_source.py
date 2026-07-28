from datetime import date, time

from bot.sources.wowquiz import WowQuizSource

_FIXTURE_GAMES = [
    {
        "id": 1,
        "franchise_id": 206,
        "title": "Назад в СССР",
        "price": 600,
        "currency": "RUB",
        "date": "2026-08-12 19:30:00",
        "bar": {"title": 'Ресторан "Кинза"', "address": "ул. Суворова, 144А"},
    },
    {
        "id": 2,
        "franchise_id": 206,
        "title": "Угадай мелодию",
        "price": 700,
        "currency": "RUB",
        "date": "2026-08-28 19:30:00",
        "bar": {"title": 'Диско-Бар "Ламбада"', "address": "ул. Плеханова, 34"},
    },
]


def test_parse_maps_real_api_shape_to_events():
    events = WowQuizSource().parse(_FIXTURE_GAMES)
    assert len(events) == 2

    first = events[0]
    assert first.title == "Назад в СССР"
    assert first.event_date == date(2026, 8, 12)
    assert first.event_time == time(19, 30)
    assert first.venue == 'Ресторан "Кинза"'
    assert first.address == "ул. Суворова, 144А"
    assert first.price == "600"
    assert first.source == "wowquiz"


def test_parse_skips_games_without_a_parsable_date():
    assert WowQuizSource().parse([{"title": "Broken", "date": None, "bar": {}}]) == []


def test_parse_handles_empty_list():
    assert WowQuizSource().parse([]) == []
