"""商品情報から紹介記事(ブログ/コラム形式)の下書きをMarkdownで生成する。"""
from __future__ import annotations

from typing import Any

from keyword_suggester import suggest_keywords

_ARTICLE_TEMPLATE = """# {item_name}を使ってみた感想

※本記事はアフィリエイトリンクを含みます。

## はじめに

{item_name}が気になっている方へ、実際の特徴や使用感をまとめました。

## 商品の特徴

- 価格: {item_price}円
- レビュー: {review_average}({review_count}件)
- 販売店: {shop_name}
{catch_copy_line}

## 使ってみた感想

{item_name}を実際に使ってみると、価格以上のクオリティで満足度が高い印象でした。
リピート購入を検討している方にもおすすめできる一品です。

## こんな人におすすめ

{recommend_line}

## まとめ

{item_name}が気になった方は、ぜひ下記からチェックしてみてください。

{affiliate_url}
"""


def generate_article(item: dict[str, Any], keywords: dict[str, list[str]] | None = None) -> str:
    """1商品につき紹介記事の下書き(Markdown)を1本生成する。"""
    if keywords is None:
        keywords = suggest_keywords(item)

    nouns = keywords.get("nouns", [])
    recommend_line = (
        f"- {'、'.join(nouns[:3])}に興味がある方" if nouns else "- コスパの良いアイテムを探している方"
    )
    catch_copy = item.get("catch_copy", "")
    catch_copy_line = f"- {catch_copy}" if catch_copy else ""

    context = {
        "item_name": item.get("item_name", ""),
        "item_price": item.get("item_price", ""),
        "review_average": item.get("review_average", 0),
        "review_count": item.get("review_count", 0),
        "shop_name": item.get("shop_name", ""),
        "catch_copy_line": catch_copy_line,
        "recommend_line": recommend_line,
        "affiliate_url": item.get("affiliate_url", ""),
    }
    return _ARTICLE_TEMPLATE.format(**context)
