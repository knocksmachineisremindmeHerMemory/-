"""成果サマリーからルールベースの改善案を提案する。

機械学習等は使わず、よくある「見るべき観点」をルール化している:
- 前期間比の増減が大きい場合の対応
- 否認率・未承認率が高い場合の注意点
- 特定商品への依存度が高い場合の分散提案
"""
from __future__ import annotations

from typing import Any

_DECLINE_THRESHOLD_PCT = -20.0
_GROWTH_THRESHOLD_PCT = 20.0
_HIGH_DENIAL_RATE = 0.2
_HIGH_UNAPPROVED_RATE = 0.3
_HIGH_CONCENTRATION_SHARE = 0.5


def build_suggestions(summary: dict[str, Any]) -> list[str]:
    suggestions: list[str] = []

    change_pct = summary.get("latest_vs_previous_pct")
    if change_pct is not None:
        if change_pct <= _DECLINE_THRESHOLD_PCT:
            suggestions.append(
                f"直近期間の成果報酬が前期間から{change_pct:.1f}%減少しています。"
                "投稿頻度を増やす、売れ筋ジャンルへシフトする、セール期間中の投稿を増やすなどを検討してください。"
            )
        elif change_pct >= _GROWTH_THRESHOLD_PCT:
            suggestions.append(
                f"直近期間の成果報酬が前期間から+{change_pct:.1f}%増加しています。"
                "伸びている商品・ジャンルを重点的に投稿すると、さらなる成長が期待できます。"
            )

    status = summary.get("status_breakdown", {}) or {}
    total_status = sum(status.values())
    if total_status > 0:
        denial_rate = status.get("否認", 0) / total_status
        if denial_rate >= _HIGH_DENIAL_RATE:
            suggestions.append(
                f"否認率が{denial_rate * 100:.0f}%と高めです。"
                "ポイント目的の購入誘導や規約に触れる投稿がないか、商品選定・訴求内容を見直してください。"
            )

        unapproved_rate = status.get("未承認", 0) / total_status
        if unapproved_rate >= _HIGH_UNAPPROVED_RATE:
            suggestions.append(
                f"未承認の件数が全体の{unapproved_rate * 100:.0f}%を占めています。"
                "承認には数週間かかることが多いため、焦らず様子を見つつ、傾向が続く場合は商品を見直してください。"
            )

    top_products = summary.get("top_products", []) or []
    total_reward = summary.get("total_reward", 0)
    if top_products and total_reward:
        top_share = top_products[0]["reward_amount"] / total_reward
        if top_share >= _HIGH_CONCENTRATION_SHARE:
            suggestions.append(
                f"「{top_products[0]['product_name']}」1商品で成果報酬全体の{top_share * 100:.0f}%を占めています。"
                "特定商品への依存度が高いため、他の商品・ジャンルへの展開も検討してください。"
            )

    if not suggestions:
        suggestions.append("特に大きな懸念点は見当たりません。現在の投稿頻度・商品選定を継続してください。")

    return suggestions
