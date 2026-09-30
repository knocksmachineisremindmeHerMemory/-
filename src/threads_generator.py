"""Threads投稿用のキャプションを複数パターン生成する。

Threadsでアフィリエイトリンクを含む投稿をする場合、景品表示法のステマ規制
(2023年施行)により広告である旨の明示が必要になる。そのため、生成する
ハッシュタグには既定で「#PR」を含める(include_disclosure=Falseで無効化できるが、
実際に開示が不要なケースであることを自分で確認した場合のみ使うこと)。
"""
from __future__ import annotations

from typing import Any

_TEMPLATES = [
    (
        "empathy",
        "最近{item_name}を使ってるんだけど、地味に生活が快適になった気がする🙂\n"
        "{item_price}円でこのクオリティは正直コスパ良すぎ…\n"
        "{hashtags}",
    ),
    (
        "question",
        "{item_name}気になってる人いる?😳\n"
        "{shop_name}で買ったけど、レビュー{review_average}のわりに実際すごく良かった。\n"
        "買って良かった?って聞かれたら迷わず「はい」って答えられる\n"
        "{hashtags}",
    ),
    (
        "problem_solution",
        "「{item_name}が欲しいけど失敗したくない」って人へ\n"
        "レビュー{review_count}件・評価{review_average}の実績があるので、個人的にはアリだと思う。\n"
        "{hashtags}",
    ),
    (
        "ranking",
        "今リピ買いしてるものランキング作るなら確実に入る子👑\n"
        "{item_name}({item_price}円)\n"
        "気になった人はチェックしてみて\n"
        "{hashtags}",
    ),
]


def _build_hashtags(extra_tags: list[str] | None, include_disclosure: bool) -> str:
    tags = []
    if include_disclosure:
        tags.append("PR")
    tags.append("楽天ROOM")
    if extra_tags:
        tags.extend(extra_tags)
    return " ".join(f"#{t}" for t in tags)


def generate_threads_posts(
    item: dict[str, Any],
    extra_tags: list[str] | None = None,
    include_disclosure: bool = True,
) -> dict[str, str]:
    """1商品につき複数パターンのThreads投稿文を生成して {パターン名: 本文} で返す。"""
    hashtags = _build_hashtags(extra_tags, include_disclosure)
    context = {
        "item_name": item.get("item_name", ""),
        "item_price": item.get("item_price", ""),
        "shop_name": item.get("shop_name", ""),
        "review_count": item.get("review_count", 0),
        "review_average": item.get("review_average", 0),
        "hashtags": hashtags,
    }

    return {name: template.format(**context) for name, template in _TEMPLATES}
