"""商品情報から楽天ROOM投稿用のキャプション下書きを複数パターン生成する。"""
from __future__ import annotations

from typing import Any

_TEMPLATES = [
    (
        "review",
        "⭐️レビュー{review_count}件・評価{review_average}の人気商品🎁\n"
        "{item_name}\n"
        "{shop_name}さんで{item_price}円、ポイント{point_rate}倍✨\n"
        "気になっていた方はチェックしてみてください🙌\n"
        "{hashtags}",
    ),
    (
        "sale",
        "【今だけ】{item_name}が{item_price}円😳\n"
        "このクオリティでこの価格はコスパ良すぎ…！\n"
        "ポイント消化にもおすすめです🛍️\n"
        "{hashtags}",
    ),
    (
        "simple",
        "最近気になっているアイテムをROOMに追加しました📝\n"
        "{item_name}\n"
        "{shop_name}さんで{item_price}円でした。\n"
        "気になる方はぜひ覗いてみてください👀\n"
        "{hashtags}",
    ),
    (
        "recommend",
        "買ってよかった🙆‍♀️\n"
        "{item_name}\n"
        "{item_price}円とは思えないクオリティで、日々の暮らしがちょっと快適になりました。\n"
        "{hashtags}",
    ),
]


def _build_hashtags(item: dict[str, Any], extra_tags: list[str] | None = None) -> str:
    tags = ["楽天ROOM", "楽天お買い物マラソン"]
    if extra_tags:
        tags.extend(extra_tags)
    return " ".join(f"#{t}" for t in tags)


def generate_drafts(item: dict[str, Any], extra_tags: list[str] | None = None) -> dict[str, str]:
    """1商品につき複数パターンのキャプション下書きを生成して {パターン名: 本文} で返す。"""
    hashtags = _build_hashtags(item, extra_tags)
    context = {
        "item_name": item.get("item_name", ""),
        "item_price": item.get("item_price", ""),
        "shop_name": item.get("shop_name", ""),
        "review_count": item.get("review_count", 0),
        "review_average": item.get("review_average", 0),
        "point_rate": item.get("point_rate", 1),
        "hashtags": hashtags,
    }

    drafts = {}
    for name, template in _TEMPLATES:
        drafts[name] = template.format(**context)
    return drafts
