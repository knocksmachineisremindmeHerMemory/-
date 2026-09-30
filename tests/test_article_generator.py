import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from article_generator import generate_article  # noqa: E402

ITEM = {
    "item_name": "テスト加湿器",
    "item_price": 3980,
    "shop_name": "テストショップ",
    "review_count": 120,
    "review_average": 4.5,
    "catch_copy": "リビングにおすすめの加湿器",
    "affiliate_url": "https://example.com/aff",
}


def test_generate_article_includes_key_fields():
    article = generate_article(ITEM)
    assert "テスト加湿器" in article
    assert "3980円" in article
    assert "https://example.com/aff" in article
    assert "アフィリエイトリンクを含みます" in article


def test_generate_article_uses_provided_keywords():
    article = generate_article(ITEM, keywords={"nouns": ["加湿", "リビング"], "search_phrases": []})
    assert "加湿" in article
    assert "リビング" in article


def test_generate_article_handles_missing_catch_copy():
    item = dict(ITEM)
    item["catch_copy"] = ""
    article = generate_article(item, keywords={"nouns": [], "search_phrases": []})
    assert "テスト加湿器" in article
