from datetime import date, time

from bot.sources.mamaquiz import MamaQuizSource

_FIXTURE_HTML = """
<html><body>
<div>Четверг 30 июля логика где? #5 Игра по мотивам ТВ-шоу "Где логика?" на ТНТ.
Только картинки и ваша логика. Harat's Pub ул. Кулакова, 7 19:30 начало игры
600 руб./чел. 120 минут 2-10 чел. в команде ЗАРЕГИСТРИРОВАТЬСЯ</div>
<div>Вторник 11 августа легкий старт #7 Ваша любимая Классика, но для команд
с рейтингом ниже 500. Достоевский ул. Славы, 10 19:30 начало игры 600 руб./чел.
120 минут 2-10 чел. в команде ЗАРЕГИСТРИРОВАТЬСЯ</div>
<div>Четверг 27 августа финал летнего сезона 2026 Закрытая игра для топовых команд.
Harat's Pub ул. Кулакова 7 19:30 начало игры 600 руб./чел. 120 минут
2-10 чел. в команде ИГРА ПО ПРИГЛАШЕНИЯМ</div>
</body></html>
"""


def test_parse_extracts_numbered_and_unnumbered_titles():
    events = MamaQuizSource().parse(_FIXTURE_HTML)
    assert len(events) == 3

    first = events[0]
    assert first.title == "логика где? #5"
    assert first.event_date == date(2026, 7, 30)
    assert first.event_time == time(19, 30)
    assert first.venue == "Harat's Pub"
    assert first.address == "ул. Кулакова, 7"
    assert first.price == "600"

    second = events[1]
    assert second.venue == "Достоевский"
    assert second.address == "ул. Славы, 10"

    third = events[2]
    assert third.title.startswith("финал летнего сезона 2026")


def test_parse_returns_empty_list_without_matching_records():
    assert MamaQuizSource().parse("<html><body>Нет игр в расписании</body></html>") == []
