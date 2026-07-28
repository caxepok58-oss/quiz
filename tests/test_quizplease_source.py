from datetime import date, time

from bot.sources.quizplease import QuizPleaseSource

_FIXTURE_PAYLOAD = {
    "status": "ok",
    "data": {
        "data": [
            {
                "id": "abc",
                "title": "Квиз, плиз! PENZA",
                "date": "28.07.2026 19:30",
                "price": 600,
                "place": {"title": "Высота 175", "address": "Пенза, ул. Володарского, 27"},
            },
            {
                "id": "def",
                "title": "[киномания] PENZA",
                "date": "29.07.2026 19:30",
                "price": 600,
                "place": {"title": "Harat's pub", "address": "Пенза, ул. Московская, 10"},
            },
        ]
    },
}


def test_parse_maps_real_api_shape_to_events():
    events = QuizPleaseSource().parse(_FIXTURE_PAYLOAD)
    assert len(events) == 2

    first = events[0]
    assert first.title == "Квиз, плиз! PENZA"
    assert first.event_date == date(2026, 7, 28)
    assert first.event_time == time(19, 30)
    assert first.venue == "Высота 175"
    assert first.address == "Пенза, ул. Володарского, 27"
    assert first.price == "600"
    assert first.source == "quizplease"


def test_parse_skips_entries_without_a_parsable_date():
    payload = {"data": {"data": [{"id": "x", "title": "Broken", "date": None, "place": {}}]}}
    assert QuizPleaseSource().parse(payload) == []


def test_parse_handles_missing_data_gracefully():
    assert QuizPleaseSource().parse({}) == []
