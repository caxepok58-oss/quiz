from datetime import date, time

from bot.sources.brainsurf import BrainSurfSource

_FIXTURE_HTML = """
<html><body>
<div class="schedule-item game-wrap game-card">
    <div class="schedule-item__content">
        <h3 class="schedule-item__title src-date_game_name">Классика 7</h3>
        <div class="schedule-item__date">
            <span class="src-date_time">3 августа, понедельник, 19:30</span>
        </div>
        <div class="schedule-item__icons">
            <div class="schedule-icon schedule-icon--location src-location game-card__location">
                г. Пенза, Ночной клуб "Достоевский"
            </div>
            <div class="schedule-icon schedule-icon--price src-price">Оргвзнос: 600</div>
        </div>
    </div>
</div>
<!-- swiper loop duplicates the same card -->
<div class="schedule-item game-wrap game-card">
    <div class="schedule-item__content">
        <h3 class="schedule-item__title src-date_game_name">Классика 7</h3>
        <div class="schedule-item__date">
            <span class="src-date_time">3 августа, понедельник, 19:30</span>
        </div>
        <div class="schedule-item__icons">
            <div class="schedule-icon schedule-icon--location src-location game-card__location">
                г. Пенза, Ночной клуб "Достоевский"
            </div>
            <div class="schedule-icon schedule-icon--price src-price">Оргвзнос: 600</div>
        </div>
    </div>
</div>
</body></html>
"""


def test_parse_extracts_and_dedups_cards():
    events = BrainSurfSource().parse(_FIXTURE_HTML)
    assert len(events) == 1

    event = events[0]
    assert event.title == "Классика 7"
    assert event.event_date == date(2026, 8, 3)
    assert event.event_time == time(19, 30)
    assert event.venue == 'Ночной клуб "Достоевский"'
    assert event.price == "600"
    assert event.source == "brainsurf"


def test_parse_returns_empty_list_without_schedule_items():
    assert BrainSurfSource().parse("<html><body>Нет игр</body></html>") == []
