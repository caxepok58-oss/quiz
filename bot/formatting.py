import textwrap
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


_COL_TIME = 6
_COL_FRANCHISE = 16
_COL_TITLE = 20
_COL_VENUE = 18
_COL_PRICE = 10


def _wrap(text: str, width: int) -> list[str]:
    text = text or ""
    return textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False) or [""]


_ROW_WIDTH = _COL_TIME + _COL_FRANCHISE + _COL_TITLE + _COL_VENUE + _COL_PRICE + 4  # + 4 "|" separators


def _row(time_col: str, franchise_col: str, title_col: str, venue_col: str, price_col: str) -> str:
    return (
        f"{time_col:<{_COL_TIME}}|"
        f"{franchise_col:<{_COL_FRANCHISE}}|"
        f"{title_col:<{_COL_TITLE}}|"
        f"{venue_col:<{_COL_VENUE}}|"
        f"{price_col:<{_COL_PRICE}}"
    )


def _render_day_table(entries: list[tuple]) -> str:
    separator = "_" * _ROW_WIDTH
    lines = [_row("Время", "Франшиза", "Игра", "Место проведения", "Стоимость"), separator]
    for event_time, title, venue, price, source in entries:
        franchise = f"{_franchise_color(source)} {_franchise_name(source)}"
        price_str = f"{price} ₽" if price else ""
        title_lines = _wrap(title or "—", _COL_TITLE)
        venue_lines = _wrap(venue or "уточняется", _COL_VENUE)
        row_height = max(len(title_lines), len(venue_lines))
        for i in range(row_height):
            lines.append(
                _row(
                    (event_time or "??:??") if i == 0 else "",
                    franchise if i == 0 else "",
                    title_lines[i] if i < len(title_lines) else "",
                    venue_lines[i] if i < len(venue_lines) else "",
                    price_str if i == 0 else "",
                )
            )
        lines.append(separator)
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
