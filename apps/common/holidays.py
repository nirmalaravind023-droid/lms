"""Holiday helpers used by the LMS calendar and due-date forms."""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from typing import Iterable
from urllib.request import urlopen

try:
    import holidays as holiday_lib
except Exception:  # pragma: no cover - fallback only if dependency is unavailable.
    holiday_lib = None


HOLIDAY_CALENDAR_META = {
    "india_national": {"label": "India National", "color": "#2563eb"},
    "hinduism": {"label": "Hindu", "color": "#f97316"},
    "islam": {"label": "Islam", "color": "#16a34a"},
    "christianity": {"label": "Christianity", "color": "#a855f7"},
    "sikhism": {"label": "Sikhism", "color": "#eab308"},
    "buddhism": {"label": "Buddhism", "color": "#0ea5e9"},
    "jainism": {"label": "Jainism", "color": "#ec4899"},
}

GOOGLE_CALENDAR_FEEDS = {
    "india_national": "https://calendar.google.com/calendar/ical/en.indian%23holiday%40group.v.calendar.google.com/public/basic.ics",
    "hinduism": "https://calendar.google.com/calendar/ical/en.hinduism%23holiday%40group.v.calendar.google.com/public/basic.ics",
    "christianity": "https://calendar.google.com/calendar/ical/en.christian%23holiday%40group.v.calendar.google.com/public/basic.ics",
    "islam": "https://calendar.google.com/calendar/ical/en.islamic%23holiday%40group.v.calendar.google.com/public/basic.ics",
}

HOLIDAY_CATEGORY_MATCHERS = (
    (
        "hinduism",
        (
            "maha shivaratri",
            "janmashtami",
            "dussehra",
            "diwali",
            "holi",
            "rama navami",
            "lohri",
            "uttarayan",
            "pongal",
            "mattu pongal",
            "uzhavar thirunal",
            "magh bihu",
            "makar sankranti",
            "vishu",
            "ugadi",
            "vasant panchami",
        ),
    ),
    ("islam", ("id-ul-fitr", "bakrid", "muharram", "milad-un-nabi", "eid", "hazarat ali", "isra and mi'raj")),
    ("christianity", ("good friday", "christmas", "easter")),
    ("sikhism", ("guru nanak jayanti", "guru gobind singh", "baisakhi")),
    ("buddhism", ("buddha purnima", "vesak")),
    ("jainism", ("mahavir jayanti", "paryushan")),
)


def _split_holiday_names(raw_label: str) -> list[str]:
    return [item.strip() for item in (raw_label or "").split(";") if item.strip()]


def _normalize_ics_text(value: str) -> str:
    return (value or "").replace("\r\n", "\n").replace("\r", "\n")


@lru_cache(maxsize=16)
def _fetch_google_ics(url: str) -> str:
    with urlopen(url, timeout=20) as response:
        return _normalize_ics_text(response.read().decode("utf-8", "ignore"))


def _parse_google_ics_events(calendar_key: str, year: int) -> list[dict[str, str]]:
    url = GOOGLE_CALENDAR_FEEDS.get(calendar_key)
    if not url:
        return []

    try:
        payload = _fetch_google_ics(url)
    except Exception:
        return []

    records: list[dict[str, str]] = []
    blocks = payload.split("BEGIN:VEVENT")
    for block in blocks[1:]:
        summary = ""
        start_date = ""
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if line.startswith("DTSTART"):
                _, _, start_date = line.partition(":")
            elif line.startswith("SUMMARY:"):
                summary = line[len("SUMMARY:"):].strip()
        if not start_date or not summary or len(start_date) < 8:
            continue
        iso_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        if not iso_date.startswith(str(year)):
            continue
        resolved_calendar_key = _detect_calendar_key(summary) if calendar_key == "india_national" else calendar_key
        calendar_meta = HOLIDAY_CALENDAR_META[resolved_calendar_key]
        records.append(
            {
                "date": iso_date,
                "label": summary,
                "scope": calendar_meta["label"],
                "calendar_key": resolved_calendar_key,
                "calendar_label": calendar_meta["label"],
                "color": calendar_meta["color"],
                "estimated": "true" if "estimated" in summary.lower() else "false",
                "source": "Google Calendar",
            }
        )
    return records


def _detect_calendar_key(label: str) -> str:
    normalized = (label or "").lower()
    for key, phrases in HOLIDAY_CATEGORY_MATCHERS:
        if any(phrase in normalized for phrase in phrases):
            return key
    return "india_national"


def get_holiday_calendars() -> list[dict[str, str]]:
    return [
        {"key": key, "label": value["label"], "color": value["color"]}
        for key, value in HOLIDAY_CALENDAR_META.items()
    ]


def get_india_holidays(year: int) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    records: list[dict[str, str]] = []

    for calendar_key in GOOGLE_CALENDAR_FEEDS:
        for item in _parse_google_ics_events(calendar_key, year):
            record_key = (item["date"], item["label"].lower(), item["calendar_key"])
            if record_key in seen:
                continue
            seen.add(record_key)
            records.append(item)

    if holiday_lib is None:
        return sorted(records, key=lambda item: (item["date"], item["label"]))

    base_holidays = holiday_lib.country_holidays("IN", years=[year])
    holiday_sources = [("India", base_holidays)]
    for subdiv in getattr(base_holidays, "subdivisions", ()):
        try:
            holiday_sources.append((subdiv, holiday_lib.country_holidays("IN", subdiv=subdiv, years=[year])))
        except Exception:
            continue

    for source_label, holiday_items in holiday_sources:
        for holiday_date, holiday_label in sorted(holiday_items.items()):
            for label_part in _split_holiday_names(str(holiday_label)):
                calendar_key = _detect_calendar_key(label_part)
                record_key = (holiday_date.isoformat(), label_part.lower(), calendar_key)
                if record_key in seen:
                    continue
                seen.add(record_key)
                calendar_meta = HOLIDAY_CALENDAR_META[calendar_key]
                is_estimated = "estimated" in label_part.lower()
                records.append(
                    {
                        "date": holiday_date.isoformat(),
                        "label": label_part,
                        "scope": calendar_meta["label"],
                        "calendar_key": calendar_key,
                        "calendar_label": calendar_meta["label"],
                        "color": calendar_meta["color"],
                        "estimated": "true" if is_estimated else "false",
                        "source": source_label,
                    }
                )
    return sorted(records, key=lambda item: (item["date"], item["label"]))


def get_india_holiday_map(years: Iterable[int]) -> dict[str, list[dict[str, str]]]:
    holiday_map: dict[str, list[dict[str, str]]] = {}
    for year in sorted(set(years)):
        holiday_map[str(year)] = get_india_holidays(year)
    return holiday_map


def group_holidays_by_day(year: int) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in get_india_holidays(year):
        grouped[item["date"]].append(item)
    return dict(grouped)
