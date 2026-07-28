import json
from datetime import date, time

from bot.sources.shakerquiz import ShakerQuizSource

_STORE = [
    ["GET/city/penza", {"id": "city-1", "name": "Пенза", "alias": "penza"}],
    [
        "GET/games/search",
        [
            {
                "id": "game-1",
                "number": "5",
                "event_time": "2026-08-05T19:30:00.000Z",
                "price": 600,
                "status": "Publish",
                "visibility": "Visible",
                "name": "МУЗЫКАЛЬНОЕ ЛОТО",
            },
            {
                "id": "game-2",
                "number": "6",
                "event_time": "2026-07-01T19:30:00.000Z",
                "price": 600,
                "status": "Finish",
                "visibility": "Visible",
                "name": "Уже прошедшая игра",
            },
        ],
    ],
    [
        "GET/games/venue/:venue/search",
        [
            {
                "id": "venue-1",
                "name": 'бар "Высота 175"',
                "street": "ул. Володарского",
                "house_number": "27",
                "game_id": "game-1",
            },
        ],
    ],
]


def _fixture_html() -> str:
    payload = {"props": {"pageProps": {"store": _STORE}}}
    return f'<html><body><script id="__NEXT_DATA__">{json.dumps(payload)}</script></body></html>'


def test_parse_joins_games_with_venue_and_converts_utc_to_moscow():
    events = ShakerQuizSource().parse(_fixture_html())
    assert len(events) == 1

    event = events[0]
    assert event.title == "МУЗЫКАЛЬНОЕ ЛОТО"
    assert event.event_date == date(2026, 8, 5)
    assert event.event_time == time(22, 30)  # 19:30 UTC + 3h (Europe/Moscow)
    assert event.venue == 'бар "Высота 175"'
    assert event.address == "ул. Володарского 27"
    assert event.price == "600"
    assert event.source == "shakerquiz"


def test_parse_filters_out_finished_games():
    events = ShakerQuizSource().parse(_fixture_html())
    titles = {e.title for e in events}
    assert "Уже прошедшая игра" not in titles


def test_parse_returns_empty_list_without_next_data_script():
    assert ShakerQuizSource().parse("<html><body>no data here</body></html>") == []
