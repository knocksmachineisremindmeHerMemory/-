"""ジャンル(カテゴリ)別の「競合の少なさ」を参考値で比較するロジック。

楽天は「そのジャンルにROOM投稿者がどれだけいるか」という競合データを
公開していないため、代わりに以下の代理指標(プロキシ)を使う:

- total_item_count: ジャンル内の総出品数(多いほど売り手側の競争は激しい傾向)
- avg_review_count: レビュー件数上位サンプルの平均レビュー数
  (低いほど「まだ強いレビュー実績を持つ定番商品が少ない」= 新規で目立ちやすい可能性)

あくまで目安であり、実際のROOM上の競合状況を保証するものではない。
"""
from __future__ import annotations

from typing import Any

from rakuten_api import get_genre_stats


def compare_genres(genre_ids: dict[str, str], sample_size: int = 30) -> list[dict[str, Any]]:
    """{表示名: genre_id} を受け取り、各ジャンルの統計を集めて返す。"""
    results = []
    for label, genre_id in genre_ids.items():
        stats = get_genre_stats(genre_id, sample_size=sample_size)
        stats["label"] = label
        results.append(stats)
    return results


def rank_by_low_competition(stats_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """avg_review_count が低い順(参考:競合が少なそうな順)に並べる。"""
    return sorted(stats_list, key=lambda s: s["avg_review_count"])
