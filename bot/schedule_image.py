import io
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .formatting import format_freshness, franchise_name

# Bundled rather than relying on system fonts: the Railway/Railpack Python image
# turned out not to ship `curl` either (see http_client.py), so nothing about
# the deploy environment's preinstalled packages can be assumed - and a bitmap
# fallback font has no Cyrillic glyphs, which is most of the text here.
_FONT_DIR = Path(__file__).parent / "assets" / "fonts"
_FONT_BOLD = _FONT_DIR / "DejaVuSans-Bold.ttf"

# Bold everywhere, sized for readability - a dedicated date column per row
# (instead of a full-width date bar) is what actually buys back the height a
# bigger font costs, since it removes one whole row per calendar day.
_FONT_SIZE = 21
_TITLE_FONT_SIZE = 28
_ROW_PADDING = 5
_CELL_PADDING = 8
_MARGIN = 20
_DATE_GAP = 12  # blank space between two different dates' row groups

# Every row is a single line - column widths are computed per-image from the
# actual text so nothing wraps or gets clipped, at the cost of a wider table.
# These caps only guard against one pathologically long title/venue blowing
# the image out; ordinary data never gets near them.
_COL_TITLE_MAX_W = 700
_COL_VENUE_MAX_W = 500

# Pastel per-franchise row backgrounds - saturated enough to tell rows apart,
# light enough that dark text stays readable without needing per-row text color.
_ROW_COLORS = {
    "quizplease": (255, 205, 210),
    "club60sec": (255, 224, 178),
    "shakerquiz": (255, 249, 196),
    "brainsurf": (200, 230, 201),
    "mamaquiz": (187, 222, 251),
    "wowquiz": (225, 190, 231),
    "mozgoboynya": (215, 204, 200),
    "manual": (224, 224, 224),
}
_DEFAULT_ROW_COLOR = (255, 255, 255)

_BG_COLOR = (255, 255, 255)
_TEXT_COLOR = (33, 33, 33)
_MUTED_TEXT_COLOR = (117, 117, 117)
_TITLE_BG = (38, 50, 56)
_TITLE_TEXT = (255, 255, 255)
_HEADER_BG = (69, 90, 100)
_HEADER_TEXT = (255, 255, 255)

_WEEKDAYS = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]

_COLUMNS = ["date", "time", "franchise", "venue", "title", "price"]
_COL_HEADERS = {
    "date": "Дата",
    "time": "Время",
    "franchise": "Франшиза",
    "venue": "Место",
    "title": "Игра",
    "price": "Цена",
}
_COL_MAX_W = {"venue": _COL_VENUE_MAX_W, "title": _COL_TITLE_MAX_W}


def _format_short_date(d: date) -> str:
    return f"{d:%d.%m.%Y} {_WEEKDAYS[d.weekday()]}"


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Truncate to a single line with an ellipsis if it doesn't fit max_width."""
    text = (text or "").strip()
    if not text or draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(f"{text}…", font=font) > max_width:
        text = text[:-1]
    return f"{text}…"


def render_schedule_image(rows, city_name: str, days_ahead: int, updated_at: str | None = None) -> bytes:
    """rows: same shape as Database.get_upcoming - (source, title, venue, address, event_date, event_time, price, url).

    Returns JPEG bytes: a table with one colored row per game (color = franchise),
    every row a single line - column widths are sized to the actual content so
    the table grows wider instead of wrapping or adding gaps between rows.
    """
    font = ImageFont.truetype(str(_FONT_BOLD), _FONT_SIZE)
    title_font = ImageFont.truetype(str(_FONT_BOLD), _TITLE_FONT_SIZE)
    line_height = _FONT_SIZE + 6
    row_height = line_height + _ROW_PADDING * 2

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    by_date: dict[str, list[tuple]] = {}
    for source, game_title, venue, _address, event_date, event_time, price, _url in rows:
        by_date.setdefault(event_date, []).append((event_time, game_title, venue, price, source))

    entries_by_date: list[tuple[str, list[tuple]]] = []
    for date_str in sorted(by_date):
        d = date.fromisoformat(date_str)
        date_label = _format_short_date(d)
        entries = sorted(by_date[date_str], key=lambda r: r[0] or "")
        cells = []
        for event_time, game_title, venue, price, source in entries:
            price_text = f"{price} ₽" if price else ""
            cells.append(
                {
                    "date": date_label,
                    "time": event_time or "??:??",
                    "franchise": franchise_name(source),
                    "venue": venue or "уточняется",
                    "title": game_title or "—",
                    "price": price_text,
                    "source": source,
                }
            )
        entries_by_date.append((date_label, cells))

    all_cells = [cell for _, cells in entries_by_date for cell in cells]

    col_width: dict[str, int] = {}
    for col in _COLUMNS:
        header_w = probe.textlength(_COL_HEADERS[col], font=font)
        content_w = max((probe.textlength(cell[col], font=font) for cell in all_cells), default=0)
        max_w = _COL_MAX_W.get(col)
        width = max(header_w, content_w)
        if max_w is not None and width > max_w:
            width = max_w
            for cell in all_cells:
                cell[col] = _fit_text(probe, cell[col], font, max_w - _CELL_PADDING)
        col_width[col] = int(width) + _CELL_PADDING * 2

    table_width = sum(col_width.values())

    title_bar_height = _TITLE_FONT_SIZE + _ROW_PADDING * 2
    header_height = _FONT_SIZE + _ROW_PADDING * 2

    total_height = _MARGIN + title_bar_height + header_height
    for date_index, (_date_label, cells) in enumerate(entries_by_date):
        if date_index > 0:
            total_height += _DATE_GAP
        total_height += row_height * len(cells)

    footer_text = format_freshness(updated_at).removeprefix("🕐 ") if updated_at else None
    footer_height = line_height + _ROW_PADDING * 2 if footer_text else 0
    total_height += footer_height + _MARGIN

    img = Image.new("RGB", (table_width + _MARGIN * 2, total_height), _BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = _MARGIN
    draw.rectangle([_MARGIN, y, _MARGIN + table_width, y + title_bar_height], fill=_TITLE_BG)
    draw.text(
        (_MARGIN + _CELL_PADDING, y + _ROW_PADDING),
        f"Квизы в г. {city_name} — расписание на {days_ahead} дней",
        font=title_font,
        fill=_TITLE_TEXT,
    )
    y += title_bar_height

    draw.rectangle([_MARGIN, y, _MARGIN + table_width, y + header_height], fill=_HEADER_BG)
    x = _MARGIN
    for col in _COLUMNS:
        draw.text((x + _CELL_PADDING, y + _ROW_PADDING), _COL_HEADERS[col], font=font, fill=_HEADER_TEXT)
        x += col_width[col]
    y += header_height

    for date_index, (_date_label, cells) in enumerate(entries_by_date):
        if date_index > 0:
            y += _DATE_GAP
        for cell in cells:
            color = _ROW_COLORS.get(cell["source"], _DEFAULT_ROW_COLOR)
            draw.rectangle([_MARGIN, y, _MARGIN + table_width, y + row_height], fill=color)
            x = _MARGIN
            for col in _COLUMNS:
                draw.text((x + _CELL_PADDING, y + _ROW_PADDING), cell[col], font=font, fill=_TEXT_COLOR)
                x += col_width[col]
            y += row_height

    if footer_text:
        draw.text((_MARGIN, y + _ROW_PADDING), footer_text, font=font, fill=_MUTED_TEXT_COLOR)

    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()
