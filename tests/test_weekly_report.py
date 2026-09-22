import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from report_analyzer import build_weekly_report, load_report_csv  # noqa: E402
from weekly_report import format_weekly_report_markdown  # noqa: E402

COLUMN_CONFIG = Path(__file__).resolve().parent.parent / "src" / "report_columns.yaml"

# 対象週: 2024-W23 (2024-06-03〜06-09), 前週: 2024-W22 (2024-05-27〜06-02)
SAMPLE_CSV = """発生日,商品名,売上金額,成果報酬額,承認状況,数量
2024/05/28,加湿器A,3980,39,承認,1
2024/05/29,コスメセットB,2500,25,承認,1
2024/06/03,加湿器A,3980,39,承認,1
2024/06/04,加湿器A,3980,39,承認,1
2024/06/07,コスメセットB,2500,25,未承認,1
2024/06/09,加湿器A,3980,39,否認,1
"""


def _write_sample_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "report.csv"
    csv_path.write_text(SAMPLE_CSV, encoding="utf-8")
    return csv_path


def test_build_weekly_report_defaults_to_latest_week(tmp_path):
    csv_path = _write_sample_csv(tmp_path)
    records = load_report_csv(csv_path, COLUMN_CONFIG)

    report = build_weekly_report(records)

    assert report["week_key"] == "2024-W23"
    assert report["week_start"] == "2024-06-03"
    assert report["week_end"] == "2024-06-09"
    assert report["total_reward"] == 142
    assert report["total_count"] == 4


def test_build_weekly_report_computes_change_pct_vs_prev_week(tmp_path):
    csv_path = _write_sample_csv(tmp_path)
    records = load_report_csv(csv_path, COLUMN_CONFIG)

    report = build_weekly_report(records, week_key="2024-W23")

    assert report["prev_week_key"] == "2024-W22"
    assert report["prev_total_reward"] == 64
    assert report["change_pct"] == ((142 - 64) / 64) * 100


def test_build_weekly_report_daily_breakdown_covers_all_seven_days(tmp_path):
    csv_path = _write_sample_csv(tmp_path)
    records = load_report_csv(csv_path, COLUMN_CONFIG)

    report = build_weekly_report(records, week_key="2024-W23")
    daily_by_date = {row["date"]: row for row in report["daily"]}

    assert len(report["daily"]) == 7
    assert daily_by_date["2024-06-03"]["reward_amount"] == 39
    assert daily_by_date["2024-06-03"]["weekday"] == "月"
    assert daily_by_date["2024-06-05"]["reward_amount"] == 0
    assert daily_by_date["2024-06-05"]["count"] == 0


def test_build_weekly_report_no_previous_week_data(tmp_path):
    csv_path = _write_sample_csv(tmp_path)
    records = load_report_csv(csv_path, COLUMN_CONFIG)

    report = build_weekly_report(records, week_key="2024-W22")

    assert report["prev_week_key"] is None
    assert report["prev_total_reward"] is None
    assert report["change_pct"] is None


def test_build_weekly_report_with_no_dated_records_returns_empty_report():
    report = build_weekly_report([])

    assert report["week_key"] is None
    assert report["total_reward"] == 0.0
    assert report["daily"] == []


def test_format_weekly_report_markdown_includes_key_sections(tmp_path):
    csv_path = _write_sample_csv(tmp_path)
    records = load_report_csv(csv_path, COLUMN_CONFIG)
    report = build_weekly_report(records, week_key="2024-W23")

    markdown = format_weekly_report_markdown(report)

    assert "2024-W23" in markdown
    assert "前週比" in markdown
    assert "## 日別推移" in markdown
    assert "## 商品別 成果報酬 上位" in markdown
    assert "## 承認状況内訳" in markdown
    assert "加湿器A" in markdown


def test_format_weekly_report_markdown_handles_no_data():
    report = build_weekly_report([])

    markdown = format_weekly_report_markdown(report)

    assert "データがありませんでした" in markdown
