import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from draft_generator import build_affiliate_block, generate_drafts  # noqa: E402


def test_generate_drafts_fills_all_templates():
    item = {
        "item_name": "テスト加湿器",
        "item_price": 3980,
        "shop_name": "テストショップ",
        "review_count": 120,
        "review_average": 4.5,
        "point_rate": 10,
    }

    drafts = generate_drafts(item, extra_tags=["加湿器"])

    assert set(drafts.keys()) == {"review", "sale", "simple", "recommend"}
    for text in drafts.values():
        assert "テスト加湿器" in text
        assert "#楽天ROOM" in text
        assert "#加湿器" in text


def test_generate_drafts_without_extra_tags():
    item = {"item_name": "商品A", "item_price": 1000, "shop_name": "店A"}
    drafts = generate_drafts(item)
    for text in drafts.values():
        assert "#楽天ROOM" in text


def test_build_affiliate_block_rakuten_only():
    item = {"item_name": "テスト加湿器", "affiliate_url": "https://hb.afl.rakuten.co.jp/example"}
    block = build_affiliate_block(item)

    assert "テスト加湿器" in block
    assert "楽天で見る" in block
    assert "Amazonで見る" not in block
    assert "広告(アフィリエイトリンク)を含みます" in block


def test_build_affiliate_block_with_asin_and_tag():
    item = {"item_name": "テスト加湿器", "affiliate_url": "https://hb.afl.rakuten.co.jp/example"}
    block = build_affiliate_block(item, asin="B0TESTASIN", amazon_tag="test-tag-22")

    assert "https://www.amazon.co.jp/dp/B0TESTASIN?tag=test-tag-22" in block
    assert "楽天で見る" in block


def test_build_affiliate_block_asin_without_tag_omits_amazon_link(monkeypatch):
    monkeypatch.delenv("AMAZON_TAG", raising=False)
    item = {"item_name": "テスト加湿器", "affiliate_url": "https://hb.afl.rakuten.co.jp/example"}
    block = build_affiliate_block(item, asin="B0TESTASIN")

    assert "Amazonで見る" not in block


def test_build_affiliate_block_without_disclosure():
    item = {"item_name": "商品A", "affiliate_url": "https://hb.afl.rakuten.co.jp/example"}
    block = build_affiliate_block(item, disclosure=False)

    assert "広告" not in block
