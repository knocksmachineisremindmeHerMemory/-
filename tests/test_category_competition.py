import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import category_competition  # noqa: E402


def _fake_stats(genre_id, sample_size=30):
    fixtures = {
        "100939": {"genre_id": "100939", "total_item_count": 5000, "sample_size": 30, "avg_review_count": 800, "avg_price": 3000, "top_items": []},
        "215783": {"genre_id": "215783", "total_item_count": 1000, "sample_size": 30, "avg_review_count": 50, "avg_price": 2000, "top_items": []},
    }
    return fixtures[genre_id]


def test_compare_genres_attaches_label():
    with patch("category_competition.get_genre_stats", side_effect=_fake_stats):
        results = category_competition.compare_genres({"コスメ": "100939", "生活雑貨": "215783"})

    labels = {r["label"] for r in results}
    assert labels == {"コスメ", "生活雑貨"}


def test_rank_by_low_competition_sorts_ascending_by_review_count():
    with patch("category_competition.get_genre_stats", side_effect=_fake_stats):
        results = category_competition.compare_genres({"コスメ": "100939", "生活雑貨": "215783"})

    ranked = category_competition.rank_by_low_competition(results)
    assert ranked[0]["label"] == "生活雑貨"
    assert ranked[1]["label"] == "コスメ"
