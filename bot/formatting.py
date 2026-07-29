from datetime import date, datetime
from html import escape

_WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
_MONTHS_GENITIVE = [
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]

_MAX_MESSAGE_LEN = 3500
_DAY_SEPARATOR = "――――――――――――――――"

_FRANCHISE_NAMES = {
    "quizplease": "Квиз, плиз!",
    "club60sec": "60 секунд",
    "shakerquiz": "Шейкер квиз",
    "brainsurf": "BrainSurf",
    "mamaquiz": "МАМАКВИЗ!",
    "wowquiz": "Вау Квиз",
    "mozgoboynya": "Мозгобойня",
    "manual": "Вручную",
}

# Telegram text formatting has no color; colored circle emoji stand in as a
# per-franchise color marker instead.
_FRANCHISE_COLORS = {
    "quizplease": "🔴",
    "club60sec": "🟠",
    "shakerquiz": "🟡",
    "brainsurf": "🟢",
    "mamaquiz": "🔵",
    "wowquiz": "🟣",
    "mozgoboynya": "🟤",
    "manual": "⚪",
}


# The 7 scraped franchises, in display order - used to build the favorites
# toggle keyboard. "manual" is intentionally excluded: it's not a franchise
# a user can follow, it's whatever the admin adds by hand.
FRANCHISE_KEYS = [
    "quizplease",
    "club60sec",
    "shakerquiz",
    "brainsurf",
    "mamaquiz",
    "wowquiz",
    "mozgoboynya",
]


def franchise_name(source: str) -> str:
    return _FRANCHISE_NAMES.get(source, source)


def franchise_color(source: str) -> str:
    return _FRANCHISE_COLORS.get(source, "⚫")


def format_date_header(d: date) -> str:
    return f"{d.day} {_MONTHS_GENITIVE[d.month]} ({_WEEKDAYS[d.weekday()]})"


def _render_day_entries(entries: list[tuple]) -> str:
    # A fixed-width "|" grid breaks on narrow phone screens: Telegram soft-wraps
    # any line too long for the viewport, splitting it mid-column and destroying
    # the alignment - a card per game (free-flowing lines, no fixed width) has
    # nothing to misalign and reads fine on any screen size.
    cards = []
    for event_time, title, venue, price, source, url in entries:
        price_str = f" · {price} ₽" if price else ""
        header_line = f"{franchise_color(source)} {event_time or '??:??'} · {franchise_name(source)}{price_str}"
        title_display = escape(title) if title else "—"
        if url:
            title_display = f'<a href="{escape(url)}">{title_display}</a>'
        cards.append(f"{header_line}\n{title_display}\n📍 {venue or 'уточняется'}")
    return "\n\n".join(cards)


def _format_freshness(updated_at: str) -> str:
    try:
        updated_dt = datetime.fromisoformat(updated_at)
    except ValueError:
        return ""
    minutes = max(0, int((datetime.utcnow() - updated_dt).total_seconds() // 60))
    if minutes < 1:
        when = "только что"
    elif minutes < 60:
        when = f"{minutes} мин. назад"
    else:
        when = f"{minutes // 60} ч. назад"
    return f"🕐 Данные обновлены: {when}"


def build_messages(rows, city_name: str, days_ahead: int, updated_at: str | None = None) -> list[str]:
    """rows: iterable of (source, title, venue, address, event_date, event_time, price, url)."""
    if not rows:
        text = f"На ближайшие {days_ahead} дней в г. {city_name} игр не найдено."
        freshness = _format_freshness(updated_at) if updated_at else ""
        return [f"{text}\n\n{freshness}" if freshness else text]

    by_date: dict[str, list[tuple]] = {}
    for source, title, venue, _address, event_date, event_time, price, url in rows:
        by_date.setdefault(event_date, []).append((event_time, title, venue, price, source, url))

    blocks = []
    for date_str in sorted(by_date):
        d = date.fromisoformat(date_str)
        entries = sorted(by_date[date_str], key=lambda r: r[0] or "")
        blocks.append(f"<b>{format_date_header(d)}</b>\n{_render_day_entries(entries)}")

    header = f"🎯 Квизы в г. {city_name} на ближайшие {days_ahead} дней:\n\n"
    messages = []
    current = header
    for block in blocks:
        piece = block if current in (header, "") else f"{_DAY_SEPARATOR}\n\n{block}"
        candidate = current + piece + "\n\n"
        if len(candidate) > _MAX_MESSAGE_LEN and current != header:
            messages.append(current.rstrip())
            current = block + "\n\n"
        else:
            current = candidate
    if current.strip():
        messages.append(current.rstrip())
    if updated_at and messages:
        freshness = _format_freshness(updated_at)
        if freshness:
            messages[-1] = f"{messages[-1]}\n\n{freshness}"
    return messages
