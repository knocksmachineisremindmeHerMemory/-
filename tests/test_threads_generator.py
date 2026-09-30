import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from threads_generator import generate_threads_posts  # noqa: E402

ITEM = {
    "item_name": "テスト加湿器",
    "item_price": 3980,
    "shop_name": "テストショップ",
    "review_count": 120,
    "review_average": 4.5,
}


def test_generate_threads_posts_includes_disclosure_by_default():
    posts = generate_threads_posts(ITEM)
    assert len(posts) == 4
    for text in posts.values():
        assert "#PR" in text
        assert "テスト加湿器" in text


def test_generate_threads_posts_can_disable_disclosure():
    posts = generate_threads_posts(ITEM, include_disclosure=False)
    for text in posts.values():
        assert "#PR" not in text


def test_generate_threads_posts_includes_extra_tags():
    posts = generate_threads_posts(ITEM, extra_tags=["加湿器"])
    for text in posts.values():
        assert "#加湿器" in text
