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


def _format_date_header(d: date) -> str:
    return f"{d.day} {_MONTHS_GENITIVE[d.month]} ({_WEEKDAYS[d.weekday()]})"


def _truncate(text: str | None, width: int) -> str:
    text = text or ""
    return text if len(text) <= width else text[: width - 1] + "…"


def _render_day_table(entries: list[tuple]) -> str:
    lines = [f"{'Время':<6}{'Игра':<30}{'Место':<20}"]
    lines.append("-" * 56)
    for event_time, title, venue, price, _source in entries:
        time_part = (event_time or "??:??").ljust(6)
        title_part = _truncate(title, 28).ljust(30)
        venue_part = _truncate(venue or "уточняется", 20)
        price_part = f"  {price}" if price else ""
        lines.append(f"{time_part}{title_part}{venue_part}{price_part}")
    return "<pre>" + "\n".join(lines) + "</pre>"


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
        blocks.append(f"<b>{_format_date_header(d)}</b>\n{_render_day_table(entries)}")

    header = f"🎯 Квизы в г. {city_name} на ближайшие {days_ahead} дней:\n\n"
    messages = []
    current = header
    for block in blocks:
        candidate = current + block + "\n\n"
        if len(candidate) > _MAX_MESSAGE_LEN and current != header:
            messages.append(current.rstrip())
            current = block + "\n\n"
        else:
            current = candidate
    if current.strip():
        messages.append(current.rstrip())
    return messages
