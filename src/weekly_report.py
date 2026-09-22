"""週次成果レポートのMarkdownフォーマット処理。

report_analyzer.build_weekly_report() の集計結果を、前週比・日別推移・
商品別ランキングを含む読みやすいMarkdownレポートに整形する。
"""
from __future__ import annotations

from typing import Any


def format_weekly_report_markdown(report: dict[str, Any]) -> str:
    if report["week_key"] is None:
        return "# 楽天ROOM 週次成果レポート\n\n対象期間のデータがありませんでした。\n"

    lines = [f"# 楽天ROOM 週次成果レポート ({report['week_start']} 〜 {report['week_end']})\n"]
    lines.append(f"- 対象週: {report['week_key']}")
    lines.append(f"- 成果報酬: ¥{report['total_reward']:,.0f}")
    lines.append(f"- 売上: ¥{report['total_sales']:,.0f}")
    lines.append(f"- 件数: {report['total_count']}")

    if report["prev_week_key"] is None:
        lines.append("- 前週比: 算出不可(前週データなし)")
    elif report["change_pct"] is None:
        lines.append(
            f"- 前週比: 算出不可(前週の成果報酬が¥0、前週実績: ¥{report['prev_total_reward']:,.0f})"
        )
    else:
        arrow = "📈" if report["change_pct"] >= 0 else "📉"
        lines.append(
            f"- 前週比: {report['change_pct']:+.1f}% {arrow} (前週: ¥{report['prev_total_reward']:,.0f})"
        )

    lines.append("\n## 日別推移\n")
    lines.append("| 日付 | 曜日 | 成果報酬 | 売上 | 件数 |")
    lines.append("|---|---|---:|---:|---:|")
    for row in report["daily"]:
        lines.append(
            f"| {row['date']} | {row['weekday']} | ¥{row['reward_amount']:,.0f} "
            f"| ¥{row['sales_amount']:,.0f} | {row['count']} |"
        )

    lines.append("\n## 商品別 成果報酬 上位\n")
    if report["top_products"]:
        lines.append("| 商品名 | 成果報酬額 | 件数 |")
        lines.append("|---|---:|---:|")
        for row in report["top_products"]:
            lines.append(f"| {row['product_name']} | ¥{row['reward_amount']:,.0f} | {row['count']} |")
    else:
        lines.append("該当データなし")

    lines.append("\n## 承認状況内訳\n")
    if report["status_breakdown"]:
        lines.append("| 状態 | 件数 |")
        lines.append("|---|---:|")
        for status, count in report["status_breakdown"].items():
            lines.append(f"| {status} | {count} |")
    else:
        lines.append("該当データなし")

    return "\n".join(lines) + "\n"
