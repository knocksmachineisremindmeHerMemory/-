"""日付ごとのイベント一覧から、カレンダーアプリ取り込み用のICS(iCalendar)を生成する。

各イベント当日を終日予定として登録し、前日にリマインド(VALARM)を付ける。
GoogleカレンダーやApple Calendarにインポートすれば、そのアプリの通知機能で
投稿タイミングのリマインドを受け取れる。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_ics(events_by_date: dict[date, list[dict[str, Any]]], reminder_days_before: int = 1) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//rakuten-room-toolkit//posting-calendar//JP",
        "CALSCALE:GREGORIAN",
    ]

    for d, events in events_by_date.items():
        summary = " / ".join(e["name"] for e in events)
        description = "\n".join(f"{e['name']}: {e['note']}" for e in events if e.get("note"))
        uid = f"{d.isoformat()}-rakuten-room-posting@toolkit"
        dtstart = d.strftime("%Y%m%d")
        dtend = (d + timedelta(days=1)).strftime("%Y%m%d")

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART;VALUE=DATE:{dtstart}",
                f"DTEND;VALUE=DATE:{dtend}",
                f"SUMMARY:{_escape('【楽天ROOM】' + summary)}",
            ]
        )
        if description:
            lines.append(f"DESCRIPTION:{_escape(description)}")
        lines.extend(
            [
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{_escape('楽天ROOM投稿リマインド: ' + summary)}",
                f"TRIGGER:-P{reminder_days_before}D",
                "END:VALARM",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
