import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from calendar_builder import build_events, group_by_date  # noqa: E402

CONFIG = {
    "recurring": [
        {"name": "5と0のつく日", "rule": "day_of_month_in", "days": [5, 10, 15, 20, 25, 30], "note": "ポイント+2倍"},
    ],
    "campaigns": [
        {"name": "楽天スーパーSALE", "start": "2026-10-08", "end": "2026-10-10", "note": "セール訴求"},
    ],
}


def test_build_events_includes_recurring_days():
    events = build_events(CONFIG, date(2026, 10, 1), date(2026, 10, 31))
    recurring_dates = {e["date"] for e in events if e["name"] == "5と0のつく日"}
    assert recurring_dates == {
        date(2026, 10, 5),
        date(2026, 10, 10),
        date(2026, 10, 15),
        date(2026, 10, 20),
        date(2026, 10, 25),
        date(2026, 10, 30),
    }


def test_build_events_includes_campaign_range():
    events = build_events(CONFIG, date(2026, 10, 1), date(2026, 10, 31))
    campaign_dates = {e["date"] for e in events if e["name"] == "楽天スーパーSALE"}
    assert campaign_dates == {date(2026, 10, 8), date(2026, 10, 9), date(2026, 10, 10)}


def test_build_events_clips_campaign_to_range():
    events = build_events(CONFIG, date(2026, 10, 9), date(2026, 10, 31))
    campaign_dates = {e["date"] for e in events if e["name"] == "楽天スーパーSALE"}
    assert campaign_dates == {date(2026, 10, 9), date(2026, 10, 10)}


def test_group_by_date_merges_same_day_events():
    events = build_events(CONFIG, date(2026, 10, 10), date(2026, 10, 10))
    grouped = group_by_date(events)
    assert list(grouped.keys()) == [date(2026, 10, 10)]
    names = {e["name"] for e in grouped[date(2026, 10, 10)]}
    assert names == {"5と0のつく日", "楽天スーパーSALE"}
