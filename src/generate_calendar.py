"""楽天ROOM 投稿カレンダー生成CLI。

src/events_config.yaml の設定(毎月繰り返しの固定イベント + 手動登録のキャンペーン期間)を
もとに、指定期間の投稿タイミング候補をMarkdown/CSV/ICSで出力する。

使い方:
    python src/generate_calendar.py --days 30
    python src/generate_calendar.py --from 2026-10-01 --to 2026-10-31
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from calendar_builder import build_events, group_by_date, load_config  # noqa: E402
from ics_builder import build_ics  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "src" / "events_config.yaml"
OUTPUT_DIR = ROOT_DIR / "output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="楽天ROOM 投稿カレンダー生成ツール")
    parser.add_argument("--days", type=int, default=30, help="今日から何日分を生成するか (デフォルト30)")
    parser.add_argument("--from", dest="date_from", help="開始日 (YYYY-MM-DD)。指定時は--daysより優先")
    parser.add_argument("--to", dest="date_to", help="終了日 (YYYY-MM-DD)。--fromとセットで指定")
    parser.add_argument("--reminder-days-before", type=int, default=1, help="ICSリマインドを何日前にするか")
    return parser


def resolve_range(args) -> tuple[date, date]:
    if args.date_from and args.date_to:
        return date.fromisoformat(args.date_from), date.fromisoformat(args.date_to)
    start = date.today()
    end = start + timedelta(days=args.days - 1)
    return start, end


def write_markdown(grouped: dict[date, list[dict]], out_path: Path, start: date, end: date) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# 楽天ROOM 投稿カレンダー ({start} 〜 {end})\n\n")
        if not grouped:
            f.write("この期間に登録済みのイベントはありません。\n")
            return
        f.write("| 日付 | イベント | メモ |\n|---|---|---|\n")
        for d, events in grouped.items():
            names = " / ".join(e["name"] for e in events)
            notes = " / ".join(e["note"] for e in events if e.get("note"))
            f.write(f"| {d} | {names} | {notes} |\n")


def write_csv(grouped: dict[date, list[dict]], out_path: Path) -> None:
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "event_names", "notes"])
        for d, events in grouped.items():
            names = " / ".join(e["name"] for e in events)
            notes = " / ".join(e["note"] for e in events if e.get("note"))
            writer.writerow([d.isoformat(), names, notes])


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if bool(args.date_from) != bool(args.date_to):
        print("--from と --to は両方指定してください。", file=sys.stderr)
        return 1

    start, end = resolve_range(args)
    if start > end:
        print("開始日は終了日より前にしてください。", file=sys.stderr)
        return 1

    config = load_config(CONFIG_PATH)
    events = build_events(config, start, end)
    grouped = group_by_date(events)

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = OUTPUT_DIR / f"posting_calendar_{timestamp}.md"
    csv_path = OUTPUT_DIR / f"posting_calendar_{timestamp}.csv"
    ics_path = OUTPUT_DIR / f"posting_calendar_{timestamp}.ics"

    write_markdown(grouped, md_path, start, end)
    write_csv(grouped, csv_path)
    ics_path.write_text(build_ics(grouped, reminder_days_before=args.reminder_days_before), encoding="utf-8")

    print(f"{len(grouped)}日分の投稿タイミング候補を生成しました ({start} 〜 {end})。")
    print(f"Markdown: {md_path}")
    print(f"CSV: {csv_path}")
    print(f"ICS(カレンダー取り込み用): {ics_path}")
    if not grouped:
        print(
            "登録済みイベントがありませんでした。src/events_config.yaml の campaigns に "
            "楽天スーパーSALEやお買い物マラソンの日程を追加してください。"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
