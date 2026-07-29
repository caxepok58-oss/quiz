import io
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .formatting import format_date_header, format_freshness, franchise_name

# Bundled rather than relying on system fonts: the Railway/Railpack Python image
# turned out not to ship `curl` either (see http_client.py), so nothing about
# the deploy environment's preinstalled packages can be assumed - and a bitmap
# fallback font has no Cyrillic glyphs, which is most of the text here.
_FONT_DIR = Path(__file__).parent / "assets" / "fonts"
_FONT_REGULAR = _FONT_DIR / "DejaVuSans.ttf"
_FONT_BOLD = _FONT_DIR / "DejaVuSans-Bold.ttf"

_FONT_SIZE = 18
_TITLE_FONT_SIZE = 26
_LINE_HEIGHT = 24
_ROW_PADDING = 8
_CELL_PADDING = 8
_MARGIN = 20

_COL_TIME_W = 80
_COL_FRANCHISE_W = 170
_COL_TITLE_W = 400
_COL_VENUE_W = 280
_COL_PRICE_W = 100
_TABLE_WIDTH = _COL_TIME_W + _COL_FRANCHISE_W + _COL_TITLE_W + _COL_VENUE_W + _COL_PRICE_W

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
_DATE_BG = (225, 225, 225)
_GRID_COLOR = (189, 189, 189)

_HEADERS = [
    ("Время", _COL_TIME_W),
    ("Франшиза", _COL_FRANCHISE_W),
    ("Игра", _COL_TITLE_W),
    ("Место проведения", _COL_VENUE_W),
    ("Цена", _COL_PRICE_W),
]

# x-offsets (from the table's left edge) of every column boundary, for grid lines.
_COLUMN_BOUNDARIES = [0]
for _, _width in _HEADERS:
    _COLUMN_BOUNDARIES.append(_COLUMN_BOUNDARIES[-1] + _width)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int = 2) -> list[str]:
    text = (text or "").strip()
    if not text:
        return [""]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    lines.append(current)

    if len(lines) <= max_lines:
        return lines

    kept = lines[:max_lines]
    last = kept[-1]
    while last and draw.textlength(f"{last}…", font=font) > max_width:
        last = last[:-1]
    kept[-1] = f"{last}…"
    return kept


def render_schedule_image(rows, city_name: str, days_ahead: int, updated_at: str | None = None) -> bytes:
    """rows: same shape as Database.get_upcoming - (source, title, venue, address, event_date, event_time, price, url).

    Returns JPEG bytes: a table with one colored row per game (color = franchise),
    grouped under a bar per date.
    """
    font = ImageFont.truetype(str(_FONT_REGULAR), _FONT_SIZE)
    font_bold = ImageFont.truetype(str(_FONT_BOLD), _FONT_SIZE)
    title_font = ImageFont.truetype(str(_FONT_BOLD), _TITLE_FONT_SIZE)

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    by_date: dict[str, list[tuple]] = {}
    for source, game_title, venue, _address, event_date, event_time, price, _url in rows:
        by_date.setdefault(event_date, []).append((event_time, game_title, venue, price, source))

    title_bar_height = _TITLE_FONT_SIZE + _ROW_PADDING * 2
    header_height = _FONT_SIZE + _ROW_PADDING * 2
    date_bar_height = _FONT_SIZE + _ROW_PADDING * 2

    layout: list[tuple] = []
    total_height = _MARGIN + title_bar_height + header_height

    for date_str in sorted(by_date):
        d = date.fromisoformat(date_str)
        layout.append(("date", format_date_header(d), date_bar_height))
        total_height += date_bar_height
        entries = sorted(by_date[date_str], key=lambda r: r[0] or "")
        for event_time, game_title, venue, price, source in entries:
            title_lines = _wrap_text(probe, game_title or "—", font, _COL_TITLE_W - _CELL_PADDING * 2)
            venue_lines = _wrap_text(probe, venue or "уточняется", font, _COL_VENUE_W - _CELL_PADDING * 2)
            n_lines = max(len(title_lines), len(venue_lines), 1)
            row_height = n_lines * _LINE_HEIGHT + _ROW_PADDING * 2
            layout.append(("row", (event_time, title_lines, venue_lines, price, source), row_height))
            total_height += row_height

    # DejaVu Sans has no color-emoji glyphs, so drop the leading icon that
    # format_freshness() adds for the (emoji-capable) Telegram text messages.
    footer_text = format_freshness(updated_at).removeprefix("🕐 ") if updated_at else None
    footer_height = _LINE_HEIGHT + _ROW_PADDING * 2 if footer_text else 0
    total_height += footer_height + _MARGIN

    img = Image.new("RGB", (_TABLE_WIDTH + _MARGIN * 2, total_height), _BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = _MARGIN
    draw.rectangle([_MARGIN, y, _MARGIN + _TABLE_WIDTH, y + title_bar_height], fill=_TITLE_BG)
    draw.text(
        (_MARGIN + _CELL_PADDING, y + _ROW_PADDING),
        f"Квизы в г. {city_name} — расписание на {days_ahead} дней",
        font=title_font,
        fill=_TITLE_TEXT,
    )
    y += title_bar_height

    draw.rectangle([_MARGIN, y, _MARGIN + _TABLE_WIDTH, y + header_height], fill=_HEADER_BG)
    x = _MARGIN
    for text, width in _HEADERS:
        draw.text((x + _CELL_PADDING, y + _ROW_PADDING), text, font=font_bold, fill=_HEADER_TEXT)
        x += width
    y += header_height

    for kind, payload, height in layout:
        if kind == "date":
            draw.rectangle([_MARGIN, y, _MARGIN + _TABLE_WIDTH, y + height], fill=_DATE_BG)
            draw.text((_MARGIN + _CELL_PADDING, y + _ROW_PADDING), payload, font=font_bold, fill=_TEXT_COLOR)
        else:
            event_time, title_lines, venue_lines, price, source = payload
            color = _ROW_COLORS.get(source, _DEFAULT_ROW_COLOR)
            draw.rectangle([_MARGIN, y, _MARGIN + _TABLE_WIDTH, y + height], fill=color)

            x = _MARGIN
            draw.text((x + _CELL_PADDING, y + _ROW_PADDING), event_time or "??:??", font=font, fill=_TEXT_COLOR)
            x += _COL_TIME_W
            draw.text((x + _CELL_PADDING, y + _ROW_PADDING), franchise_name(source), font=font, fill=_TEXT_COLOR)
            x += _COL_FRANCHISE_W
            for i, line in enumerate(title_lines):
                draw.text((x + _CELL_PADDING, y + _ROW_PADDING + i * _LINE_HEIGHT), line, font=font, fill=_TEXT_COLOR)
            x += _COL_TITLE_W
            for i, line in enumerate(venue_lines):
                draw.text((x + _CELL_PADDING, y + _ROW_PADDING + i * _LINE_HEIGHT), line, font=font, fill=_TEXT_COLOR)
            x += _COL_VENUE_W
            price_text = f"{price} ₽" if price else ""
            draw.text((x + _CELL_PADDING, y + _ROW_PADDING), price_text, font=font, fill=_TEXT_COLOR)

        for boundary in _COLUMN_BOUNDARIES:
            x_line = _MARGIN + boundary
            draw.line([x_line, y, x_line, y + height], fill=_GRID_COLOR)
        draw.line([_MARGIN, y + height, _MARGIN + _TABLE_WIDTH, y + height], fill=_GRID_COLOR)
        y += height

    if footer_text:
        draw.text((_MARGIN, y + _ROW_PADDING), footer_text, font=font, fill=_MUTED_TEXT_COLOR)

    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()
