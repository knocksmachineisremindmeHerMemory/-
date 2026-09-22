import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ics_builder import build_ics  # noqa: E402


def test_build_ics_contains_event_and_alarm():
    events_by_date = {
        date(2026, 10, 10): [{"name": "5と0のつく日", "note": "ポイント+2倍"}],
    }

    ics = build_ics(events_by_date, reminder_days_before=1)

    assert "BEGIN:VCALENDAR" in ics
    assert "END:VCALENDAR" in ics
    assert "DTSTART;VALUE=DATE:20261010" in ics
    assert "DTEND;VALUE=DATE:20261011" in ics
    assert "SUMMARY:【楽天ROOM】5と0のつく日" in ics
    assert "BEGIN:VALARM" in ics
    assert "TRIGGER:-P1D" in ics
    assert ics.count("BEGIN:VEVENT") == 1


def test_build_ics_merges_multiple_events_same_day():
    events_by_date = {
        date(2026, 10, 10): [
            {"name": "5と0のつく日", "note": ""},
            {"name": "楽天スーパーSALE", "note": "セール訴求"},
        ],
    }

    ics = build_ics(events_by_date)

    assert "5と0のつく日 / 楽天スーパーSALE" in ics
    assert ics.count("BEGIN:VEVENT") == 1


def test_build_ics_escapes_commas_in_description():
    events_by_date = {
        date(2026, 10, 1): [{"name": "テスト,イベント", "note": "注意,事項"}],
    }

    ics = build_ics(events_by_date)
    assert "テスト\\,イベント" in ics
