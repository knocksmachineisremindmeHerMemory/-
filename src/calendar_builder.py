"""楽天ROOM投稿カレンダーの生成ロジック。

events_config.yaml の recurring(毎月繰り返し)・campaigns(都度アナウンスされる
キャンペーン期間)を指定期間分展開し、日付ごとのイベント一覧を作る。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import yaml


def load_config(path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _expand_recurring(rule: dict[str, Any], start: date, end: date) -> list[dict[str, Any]]:
    events = []
    if rule.get("rule") != "day_of_month_in":
        return events
    days = set(rule.get("days", []))
    current = start
    while current <= end:
        if current.day in days:
            events.append({"date": current, "name": rule["name"], "note": rule.get("note", "")})
        current += timedelta(days=1)
    return events


def _expand_campaign(campaign: dict[str, Any], start: date, end: date) -> list[dict[str, Any]]:
    c_start = date.fromisoformat(str(campaign["start"]))
    c_end = date.fromisoformat(str(campaign["end"]))
    range_start = max(c_start, start)
    range_end = min(c_end, end)

    events = []
    current = range_start
    while current <= range_end:
        events.append({"date": current, "name": campaign["name"], "note": campaign.get("note", "")})
        current += timedelta(days=1)
    return events


def build_events(config: dict[str, Any], start: date, end: date) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for rule in config.get("recurring", []) or []:
        events.extend(_expand_recurring(rule, start, end))
    for campaign in config.get("campaigns", []) or []:
        events.extend(_expand_campaign(campaign, start, end))
    events.sort(key=lambda e: (e["date"], e["name"]))
    return events


def group_by_date(events: list[dict[str, Any]]) -> dict[date, list[dict[str, Any]]]:
    grouped: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for e in events:
        grouped[e["date"]].append(e)
    return dict(sorted(grouped.items()))
