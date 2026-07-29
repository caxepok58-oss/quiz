from datetime import datetime, timedelta

from bot.formatting import build_messages


def test_build_messages_empty():
    messages = build_messages([], "Пенза", 30)
    assert len(messages) == 1
    assert "не найдено" in messages[0]


def test_build_messages_appends_freshness_footer():
    rows = [("quizplease", "Игра", "Место", None, "2026-08-05", "19:00", None, None)]
    updated_at = (datetime.utcnow() - timedelta(minutes=90)).isoformat()

    messages = build_messages(rows, "Пенза", 30, updated_at)

    assert "обновлены" in messages[-1]
    assert "1 ч." in messages[-1]


def test_build_messages_without_updated_at_has_no_footer():
    rows = [("quizplease", "Игра", "Место", None, "2026-08-05", "19:00", None, None)]
    messages = build_messages(rows, "Пенза", 30)
    assert "обновлены" not in messages[-1]


def test_build_messages_groups_by_date_and_includes_fields():
    rows = [
        ("quizplease", "Квиз, плиз! Игра 3", 'Бар "Огни"', None, "2026-08-05", "19:00", "500", "http://x"),
        ("manual", "Свой квиз", "Клуб Х", None, "2026-08-05", "20:30", None, None),
    ]
    messages = build_messages(rows, "Пенза", 30)
    assert len(messages) == 1
    text = messages[0]
    assert "Пенза" in text
    assert "Квиз, плиз! Игра 3" in text
    assert "Огни" in text
    assert "19:00" in text
    assert "20:30" in text


def test_build_messages_splits_when_too_long():
    rows = [
        ("quizplease", f"Игра номер {i}", "Место", None, f"2026-08-{(i % 28) + 1:02d}", "19:00", None, None)
        for i in range(200)
    ]
    messages = build_messages(rows, "Пенза", 30)
    assert len(messages) > 1
    for message in messages:
        assert len(message) <= 3600
