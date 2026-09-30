"""楽天ランキングのスナップショットを保存し、前回との順位変動から「伸びている商品」を検出する。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _item_key(item: dict[str, Any]) -> str:
    code = item.get("item_code")
    if code:
        return code
    return f"{item.get('shop_name', '')}:{item.get('item_name', '')}"


def load_snapshot(path: Path) -> list[dict[str, Any]] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("items", [])


def save_snapshot(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now().isoformat(),
        "items": [{"item_code": _item_key(i), "rank": i["rank"], "item_name": i["item_name"]} for i in items],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_rank_changes(
    previous_items: list[dict[str, Any]] | None,
    current_items: list[dict[str, Any]],
    rising_threshold: int = 5,
) -> list[dict[str, Any]]:
    """前回スナップショットと比較し、各商品に順位変動と状態(new_entry/rising/falling/stable)を付与する。

    previous_items が None(初回実行でスナップショットが無い)の場合は全件 status="unknown" とする。
    """
    if previous_items is None:
        return [{**item, "previous_rank": None, "rank_change": None, "status": "unknown"} for item in current_items]

    prev_by_key = {_item_key(p): p["rank"] for p in previous_items}

    changes = []
    for item in current_items:
        key = _item_key(item)
        prev_rank = prev_by_key.get(key)
        if prev_rank is None:
            changes.append({**item, "previous_rank": None, "rank_change": None, "status": "new_entry"})
            continue

        rank_change = prev_rank - item["rank"]
        if rank_change >= rising_threshold:
            status = "rising"
        elif rank_change <= -rising_threshold:
            status = "falling"
        else:
            status = "stable"
        changes.append({**item, "previous_rank": prev_rank, "rank_change": rank_change, "status": status})

    return changes


def filter_growing(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in changes if c["status"] in ("new_entry", "rising")]
