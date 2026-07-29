from datetime import date, time

from bot.sources.heuristic import HeuristicScheduleSource

_FIXTURE_HTML = """
<html><body>
<div class="schedule-list">
  <div class="game-card">
    <h3>Квиз, плиз! Сезон 15 Игра 3</h3>
    <div class="card-date">28 июля 2026, 19:00</div>
    <div class="card-venue">Бар "Огни", ул. Московская 10</div>
  </div>
  <div class="game-card">
    <h3>Мемный квиз</h3>
    <div class="card-date">4 августа 2026, 20:00</div>
    <div class="card-venue">Клуб "Плюшка"</div>
  </div>
</div>
</body></html>
"""


def test_parse_extracts_events_from_card_like_blocks():
    source = HeuristicScheduleSource(name="test", url="http://example.test/schedule")
    events = source.parse(_FIXTURE_HTML)

    titles = {e.title for e in events}
    assert "Квиз, плиз! Сезон 15 Игра 3" in titles
    assert "Мемный квиз" in titles

    first = next(e for e in events if e.title == "Квиз, плиз! Сезон 15 Игра 3")
    assert first.event_date == date(2026, 7, 28)
    assert first.event_time == time(19, 0)
    assert first.source == "test"


def test_parse_ignores_blocks_without_a_date():
    source = HeuristicScheduleSource(name="test", url="http://example.test/schedule")
    events = source.parse("<html><body><div>Просто текст без даты</div></body></html>")
    assert events == []


def test_parse_collapses_two_cards_sharing_the_same_date_and_time():
    # A title that itself embeds the date/time ("...играем 29 июля...") can
    # get card-expanded separately from the actual date/venue block next to
    # it, producing two rows for one real game. Both share date+time, so
    # only the fuller card (the one with more surrounding text) should survive.
    html = """
    <html><body>
    <div class="game-row">
      <div class="title">Игра головой | 4 игра играем 29 июля, среда 19:30 клуб Достоевский</div>
      <div class="date-venue">29 июля 2026, 19:30 клуб Достоевский 500</div>
    </div>
    </body></html>
    """
    source = HeuristicScheduleSource(name="test", url="http://example.test/schedule")
    events = source.parse(html)

    matching = [e for e in events if e.event_date == date(2026, 7, 29) and e.event_time == time(19, 30)]
    assert len(matching) == 1
