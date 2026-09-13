import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from report_analyzer import (  # noqa: E402
    aggregate_by_period,
    aggregate_by_product,
    build_summary,
    load_report_csv,
    status_breakdown,
)

COLUMN_CONFIG = Path(__file__).resolve().parent.parent / "src" / "report_columns.yaml"

SAMPLE_CSV = """発生日,商品名,売上金額,成果報酬額,承認状況,数量
2024/06/01,加湿器A,3980,39,承認,1
2024/06/03,加湿器A,3980,39,承認,1
2024/06/10,コスメセットB,2500,25,未承認,1
2024/07/02,加湿器A,3980,39,承認,1
2024/07/05,コスメセットB,2500,25,否認,1
"""


def _write_sample_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "report.csv"
    csv_path.write_text(SAMPLE_CSV, encoding="utf-8")
    return csv_path


def test_load_report_csv_parses_rows(tmp_path):
    csv_path = _write_sample_csv(tmp_path)
    records = load_report_csv(csv_path, COLUMN_CONFIG)

    assert len(records) == 5
    assert records[0]["product_name"] == "加湿器A"
    assert records[0]["reward_amount"] == 39
    assert records[0]["date"].strftime("%Y-%m-%d") == "2024-06-01"


def test_aggregate_by_period_groups_by_month(tmp_path):
    csv_path = _write_sample_csv(tmp_path)
    records = load_report_csv(csv_path, COLUMN_CONFIG)

    by_period = aggregate_by_period(records, period="month")
    periods = {row["period"]: row for row in by_period}

    assert periods["2024-06"]["reward_amount"] == 103
    assert periods["2024-06"]["count"] == 3
    assert periods["2024-07"]["reward_amount"] == 64


def test_aggregate_by_product_sorts_desc(tmp_path):
    csv_path = _write_sample_csv(tmp_path)
    records = load_report_csv(csv_path, COLUMN_CONFIG)

    top_products = aggregate_by_product(records, top_n=10)

    assert top_products[0]["product_name"] == "加湿器A"
    assert top_products[0]["reward_amount"] == 117


def test_status_breakdown(tmp_path):
    csv_path = _write_sample_csv(tmp_path)
    records = load_report_csv(csv_path, COLUMN_CONFIG)

    breakdown = status_breakdown(records)

    assert breakdown == {"承認": 3, "未承認": 1, "否認": 1}


def test_build_summary_includes_change_pct(tmp_path):
    csv_path = _write_sample_csv(tmp_path)
    records = load_report_csv(csv_path, COLUMN_CONFIG)

    summary = build_summary(records, period="month", top_n=5)

    assert summary["total_reward"] == 167
    assert summary["total_records"] == 5
    assert summary["latest_vs_previous_pct"] is not None
