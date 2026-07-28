"""Helpers for pulling Russian dates/times out of free-form page text.

Used by the heuristic scraper (bot/sources/heuristic.py) because we could
not inspect the live markup of the target sites to write exact selectors.
"""
import re
from datetime import date, time, timedelta

_MONTH_STEMS = {
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "май": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}

_DATE_RE = re.compile(
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>январ\w*|феврал\w*|март\w*|апрел\w*|ма[йя]\w*|"
    r"июн\w*|июл\w*|август\w*|сентябр\w*|октябр\w*|ноябр\w*|декабр\w*)"
    r"(?:\s+(?P<year>\d{4}))?",
    re.IGNORECASE,
)
_TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")


def find_date(text: str, today: date) -> date | None:
    match = _DATE_RE.search(text)
    if not match:
        return None
    month = _MONTH_STEMS.get(match.group("month").lower()[:3])
    if not month:
        return None
    day = int(match.group("day"))
    year = int(match.group("year")) if match.group("year") else today.year
    try:
        result = date(year, month, day)
    except ValueError:
        return None
    if not match.group("year") and result < today - timedelta(days=2):
        result = date(year + 1, month, day)
    return result


def find_time(text: str) -> time | None:
    match = _TIME_RE.search(text)
    if not match:
        return None
    return time(int(match.group(1)), int(match.group(2)))


def count_dates(text: str) -> int:
    return len(_DATE_RE.findall(text))
