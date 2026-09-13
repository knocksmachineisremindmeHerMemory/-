import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from draft_generator import generate_drafts  # noqa: E402


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
