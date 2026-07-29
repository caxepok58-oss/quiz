import io

from PIL import Image

from bot.schedule_image import render_schedule_image, _ROW_COLORS


def test_render_schedule_image_returns_valid_jpeg():
    rows = [
        ("quizplease", "Игра А", 'Бар "Огни"', None, "2026-08-05", "19:00", "500", None),
        ("shakerquiz", "Игра Б", "Высота 175", None, "2026-08-05", "20:30", "600", None),
    ]
    data = render_schedule_image(rows, "Пенза", 30)

    assert data[:2] == b"\xff\xd8"  # JPEG magic bytes
    img = Image.open(io.BytesIO(data))
    assert img.format == "JPEG"
    assert img.width > 0 and img.height > 0


def test_render_schedule_image_grows_taller_with_more_games():
    few_rows = [("quizplease", "Игра А", "Место", None, "2026-08-05", "19:00", None, None)]
    many_rows = [
        ("quizplease", "Игра А", "Место", None, "2026-08-05", f"{10 + i}:00", None, None) for i in range(20)
    ]

    short_img = Image.open(io.BytesIO(render_schedule_image(few_rows, "Пенза", 30)))
    tall_img = Image.open(io.BytesIO(render_schedule_image(many_rows, "Пенза", 30)))

    assert tall_img.height > short_img.height
    assert tall_img.width == short_img.width


def test_render_schedule_image_wraps_long_titles_without_crashing():
    rows = [
        (
            "wowquiz",
            "Очень длинное название игры про кино, музыку и вообще всё на свете сразу",
            'Ресторан "Очень длинное название заведения тоже"',
            None,
            "2026-08-05",
            "19:30",
            "600",
            None,
        )
    ]
    data = render_schedule_image(rows, "Пенза", 30)
    assert data[:2] == b"\xff\xd8"


def test_every_franchise_has_a_distinct_row_color():
    colors = list(_ROW_COLORS.values())
    assert len(colors) == len(set(colors))
