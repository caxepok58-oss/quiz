from datetime import date

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


def _franchise_name(source: str) -> str:
    return _FRANCHISE_NAMES.get(source, source)


def _franchise_color(source: str) -> str:
    return _FRANCHISE_COLORS.get(source, "⚫")


def _format_date_header(d: date) -> str:
    return f"{d.day} {_MONTHS_GENITIVE[d.month]} ({_WEEKDAYS[d.weekday()]})"


def _render_day_entries(entries: list[tuple]) -> str:
    # A fixed-width "|" grid breaks on narrow phone screens: Telegram soft-wraps
    # any line too long for the viewport, splitting it mid-column and destroying
    # the alignment - a card per game (free-flowing lines, no fixed width) has
    # nothing to misalign and reads fine on any screen size.
    cards = []
    for event_time, title, venue, price, source in entries:
        price_str = f" · {price} ₽" if price else ""
        header_line = f"{_franchise_color(source)} {event_time or '??:??'} · {_franchise_name(source)}{price_str}"
        cards.append(f"{header_line}\n{title or '—'}\n📍 {venue or 'уточняется'}")
    return "\n\n".join(cards)


def build_messages(rows, city_name: str, days_ahead: int) -> list[str]:
    """rows: iterable of (source, title, venue, address, event_date, event_time, price, url)."""
    if not rows:
        return [f"На ближайшие {days_ahead} дней в г. {city_name} игр не найдено."]

    by_date: dict[str, list[tuple]] = {}
    for source, title, venue, _address, event_date, event_time, price, _url in rows:
        by_date.setdefault(event_date, []).append((event_time, title, venue, price, source))

    blocks = []
    for date_str in sorted(by_date):
        d = date.fromisoformat(date_str)
        entries = sorted(by_date[date_str], key=lambda r: r[0] or "")
        blocks.append(f"<b>{_format_date_header(d)}</b>\n{_render_day_entries(entries)}")

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
    return messages
