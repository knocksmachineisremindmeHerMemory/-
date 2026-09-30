"""楽天アフィリエイトの成果報酬レポート(CSV)を集計・分析する。

楽天アフィリエイトには成果データを取得する公開APIが無いため、
アフィリエイト管理画面(https://affiliate.rakuten.co.jp/)からダウンロードした
「成果報酬レポート」CSVを入力として使う。列名はダウンロード時期やレポート種別で
変わることがあるため、report_columns.yaml の候補リストから自動検出する。
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

_DATE_FORMATS = ["%Y/%m/%d", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"]
_WEEKDAY_LABELS = ["月", "火", "水", "木", "金", "土", "日"]


class ReportParseError(RuntimeError):
    pass


def load_column_map(column_config_path: Path) -> dict[str, list[str]]:
    with open(column_config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _detect_columns(header: list[str], candidates: dict[str, list[str]]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for field, names in candidates.items():
        for name in names:
            if name in header:
                resolved[field] = name
                break
    missing = [f for f in ("date", "reward_amount") if f not in resolved]
    if missing:
        raise ReportParseError(
            "CSVの必須列が見つかりませんでした: "
            f"{missing}。src/report_columns.yaml に実際の列名を追加してください。 "
            f"CSVのヘッダー: {header}"
        )
    return resolved


def _parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_number(value: str) -> float:
    if value is None:
        return 0.0
    cleaned = str(value).replace(",", "").replace("円", "").strip()
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def load_report_csv(csv_path: Path, column_config_path: Path) -> list[dict[str, Any]]:
    candidates = load_column_map(column_config_path)

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ReportParseError("CSVが空です。")

    header = rows[0]
    col_map = _detect_columns(header, candidates)

    records = []
    for raw_row in rows[1:]:
        if not raw_row or all(not cell.strip() for cell in raw_row):
            continue
        row = dict(zip(header, raw_row))
        date_value = _parse_date(row.get(col_map.get("date", ""), ""))
        records.append(
            {
                "date": date_value,
                "product_name": row.get(col_map.get("product_name", ""), "").strip(),
                "sales_amount": _parse_number(row.get(col_map.get("sales_amount", ""), "0")),
                "reward_amount": _parse_number(row.get(col_map.get("reward_amount", ""), "0")),
                "status": row.get(col_map.get("status", ""), "").strip(),
                "quantity": _parse_number(row.get(col_map.get("quantity", ""), "0")),
            }
        )
    return records


def _period_key(dt: datetime | None, period: str) -> str:
    if dt is None:
        return "不明"
    if period == "day":
        return dt.strftime("%Y-%m-%d")
    if period == "week":
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return dt.strftime("%Y-%m")


def aggregate_by_period(records: list[dict[str, Any]], period: str = "month") -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"reward": 0.0, "sales": 0.0, "count": 0})
    for r in records:
        key = _period_key(r["date"], period)
        buckets[key]["reward"] += r["reward_amount"]
        buckets[key]["sales"] += r["sales_amount"]
        buckets[key]["count"] += 1

    result = [
        {"period": key, "reward_amount": v["reward"], "sales_amount": v["sales"], "count": v["count"]}
        for key, v in buckets.items()
    ]
    result.sort(key=lambda x: x["period"])
    return result


def aggregate_by_product(records: list[dict[str, Any]], top_n: int = 10) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"reward": 0.0, "sales": 0.0, "count": 0})
    for r in records:
        name = r["product_name"] or "(商品名不明)"
        buckets[name]["reward"] += r["reward_amount"]
        buckets[name]["sales"] += r["sales_amount"]
        buckets[name]["count"] += 1

    result = [
        {"product_name": name, "reward_amount": v["reward"], "sales_amount": v["sales"], "count": v["count"]}
        for name, v in buckets.items()
    ]
    result.sort(key=lambda x: x["reward_amount"], reverse=True)
    return result[:top_n]


def status_breakdown(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for r in records:
        status = r["status"] or "不明"
        counts[status] += 1
    return dict(counts)


def _iso_week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _iso_week_bounds(week_key: str) -> tuple[date, date]:
    year_str, week_str = week_key.split("-W")
    year, week = int(year_str), int(week_str)
    start = date.fromisocalendar(year, week, 1)
    end = date.fromisocalendar(year, week, 7)
    return start, end


def _prev_week_key(week_key: str) -> str:
    start, _ = _iso_week_bounds(week_key)
    prev_day = start - timedelta(days=1)
    return _iso_week_key(prev_day)


def build_weekly_report(records: list[dict[str, Any]], week_key: str | None = None, top_n: int = 10) -> dict[str, Any]:
    """指定週(なければデータ中の最新週)の実績を、前週比・日別内訳付きで集計する。"""
    dated_records = [r for r in records if r["date"] is not None]

    if week_key is None:
        if not dated_records:
            return {
                "week_key": None,
                "week_start": None,
                "week_end": None,
                "total_reward": 0.0,
                "total_sales": 0.0,
                "total_count": 0,
                "prev_week_key": None,
                "prev_total_reward": None,
                "change_pct": None,
                "daily": [],
                "top_products": [],
                "status_breakdown": {},
            }
        week_key = _iso_week_key(max(r["date"] for r in dated_records).date())

    week_start, week_end = _iso_week_bounds(week_key)
    week_records = [r for r in dated_records if week_start <= r["date"].date() <= week_end]

    prev_week_key = _prev_week_key(week_key)
    prev_start, prev_end = _iso_week_bounds(prev_week_key)
    prev_records = [r for r in dated_records if prev_start <= r["date"].date() <= prev_end]

    total_reward = sum(r["reward_amount"] for r in week_records)
    total_sales = sum(r["sales_amount"] for r in week_records)
    prev_total_reward = sum(r["reward_amount"] for r in prev_records) if prev_records else None

    change_pct = None
    if prev_total_reward:
        change_pct = (total_reward - prev_total_reward) / prev_total_reward * 100

    daily_buckets: dict[date, dict[str, float]] = {
        week_start + timedelta(days=i): {"reward": 0.0, "sales": 0.0, "count": 0} for i in range(7)
    }
    for r in week_records:
        bucket = daily_buckets[r["date"].date()]
        bucket["reward"] += r["reward_amount"]
        bucket["sales"] += r["sales_amount"]
        bucket["count"] += 1

    daily = [
        {
            "date": d.strftime("%Y-%m-%d"),
            "weekday": _WEEKDAY_LABELS[d.weekday()],
            "reward_amount": v["reward"],
            "sales_amount": v["sales"],
            "count": v["count"],
        }
        for d, v in sorted(daily_buckets.items())
    ]

    return {
        "week_key": week_key,
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "total_reward": total_reward,
        "total_sales": total_sales,
        "total_count": len(week_records),
        "prev_week_key": prev_week_key if prev_records else None,
        "prev_total_reward": prev_total_reward,
        "change_pct": change_pct,
        "daily": daily,
        "top_products": aggregate_by_product(week_records, top_n=top_n),
        "status_breakdown": status_breakdown(week_records),
    }


def build_summary(records: list[dict[str, Any]], period: str = "month", top_n: int = 10) -> dict[str, Any]:
    total_reward = sum(r["reward_amount"] for r in records)
    total_sales = sum(r["sales_amount"] for r in records)

    by_period = aggregate_by_period(records, period=period)
    prev_reward = None
    change_pct = None
    if len(by_period) >= 2:
        prev_reward = by_period[-2]["reward_amount"]
        latest_reward = by_period[-1]["reward_amount"]
        if prev_reward:
            change_pct = (latest_reward - prev_reward) / prev_reward * 100

    return {
        "total_reward": total_reward,
        "total_sales": total_sales,
        "total_records": len(records),
        "by_period": by_period,
        "top_products": aggregate_by_product(records, top_n=top_n),
        "status_breakdown": status_breakdown(records),
        "latest_vs_previous_pct": change_pct,
    }
