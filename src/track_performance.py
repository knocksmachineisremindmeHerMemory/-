"""楽天アフィリエイト成果報酬レポート(CSV)の集計・ダッシュボード生成CLI。

楽天アフィリエイトは成果データを取得する公開APIを提供していないため、
https://affiliate.rakuten.co.jp/ の管理画面から「成果報酬レポート」CSVを
手動でダウンロードし、そのファイルをこのツールに渡して分析する。

使い方:
    python src/track_performance.py --csv path/to/report.csv --period month --top 10
"""
from __future__ import annotations

import argparse
import csv as csv_module
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from dashboard_builder import build_dashboard_html  # noqa: E402
from report_analyzer import ReportParseError, build_summary, load_report_csv  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
COLUMN_CONFIG = ROOT_DIR / "src" / "report_columns.yaml"
OUTPUT_DIR = ROOT_DIR / "output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="楽天アフィリエイト成果レポートの集計・ダッシュボード生成")
    parser.add_argument("--csv", required=True, help="楽天アフィリエイト管理画面からダウンロードしたCSVのパス")
    parser.add_argument("--period", default="month", choices=["day", "week", "month"], help="集計単位")
    parser.add_argument("--top", type=int, default=10, help="商品別ランキングの表示件数")
    return parser


def write_markdown(summary: dict, out_path: Path) -> None:
    change_pct = summary.get("latest_vs_previous_pct")
    change_str = f"{change_pct:+.1f}%" if change_pct is not None else "算出不可(データ不足)"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# 楽天ROOM 成果レポート サマリー\n\n")
        f.write(f"- 累計成果報酬: ¥{summary['total_reward']:,.0f}\n")
        f.write(f"- 累計売上: ¥{summary['total_sales']:,.0f}\n")
        f.write(f"- 件数: {summary['total_records']}\n")
        f.write(f"- 直近期間 vs 前期間: {change_str}\n\n")

        f.write("## 期間別 成果報酬\n\n")
        f.write("| 期間 | 成果報酬額 | 売上額 | 件数 |\n|---|---:|---:|---:|\n")
        for row in summary["by_period"]:
            f.write(f"| {row['period']} | ¥{row['reward_amount']:,.0f} | ¥{row['sales_amount']:,.0f} | {row['count']} |\n")

        f.write("\n## 商品別 成果報酬 上位\n\n")
        f.write("| 商品名 | 成果報酬額 | 件数 |\n|---|---:|---:|\n")
        for row in summary["top_products"]:
            f.write(f"| {row['product_name']} | ¥{row['reward_amount']:,.0f} | {row['count']} |\n")

        f.write("\n## 承認状況内訳\n\n")
        f.write("| 状態 | 件数 |\n|---|---:|\n")
        for status, count in summary["status_breakdown"].items():
            f.write(f"| {status} | {count} |\n")


def write_period_csv(summary: dict, out_path: Path) -> None:
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv_module.DictWriter(f, fieldnames=["period", "reward_amount", "sales_amount", "count"])
        writer.writeheader()
        for row in summary["by_period"]:
            writer.writerow(row)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"エラー: CSVファイルが見つかりません: {csv_path}", file=sys.stderr)
        return 1

    try:
        records = load_report_csv(csv_path, COLUMN_CONFIG)
    except ReportParseError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    if not records:
        print("CSVにデータ行がありませんでした。")
        return 0

    summary = build_summary(records, period=args.period, top_n=args.top)

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = OUTPUT_DIR / f"performance_summary_{timestamp}.md"
    csv_out_path = OUTPUT_DIR / f"performance_by_period_{timestamp}.csv"
    html_path = OUTPUT_DIR / f"performance_dashboard_{timestamp}.html"

    write_markdown(summary, md_path)
    write_period_csv(summary, csv_out_path)
    html_path.write_text(build_dashboard_html(summary), encoding="utf-8")

    print(f"{summary['total_records']}件のデータを集計しました。")
    print(f"サマリー: {md_path}")
    print(f"期間別CSV: {csv_out_path}")
    print(f"ダッシュボード: {html_path} (ブラウザで開いて確認してください)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
