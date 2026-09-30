import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ranking_tracker import compute_rank_changes, filter_growing, load_snapshot, save_snapshot  # noqa: E402


def _item(item_code, rank, name="商品"):
    return {"item_code": item_code, "rank": rank, "item_name": name, "shop_name": "店"}


def test_compute_rank_changes_first_run_returns_unknown():
    current = [_item("A", 1), _item("B", 2)]
    changes = compute_rank_changes(None, current)
    assert all(c["status"] == "unknown" for c in changes)


def test_compute_rank_changes_detects_new_entry_and_rising():
    previous = [_item("A", 10), _item("B", 3)]
    current = [_item("A", 1), _item("B", 2), _item("C", 5)]

    changes = compute_rank_changes(previous, current, rising_threshold=5)
    by_code = {c["item_code"]: c for c in changes}

    assert by_code["A"]["status"] == "rising"
    assert by_code["A"]["rank_change"] == 9
    assert by_code["B"]["status"] == "stable"
    assert by_code["C"]["status"] == "new_entry"


def test_filter_growing_keeps_only_new_entry_and_rising():
    changes = [
        {"status": "new_entry"},
        {"status": "rising"},
        {"status": "stable"},
        {"status": "falling"},
    ]
    growing = filter_growing(changes)
    assert len(growing) == 2


def test_save_and_load_snapshot_roundtrip(tmp_path):
    path = tmp_path / "genre.json"
    items = [_item("A", 1), _item("B", 2)]

    save_snapshot(path, items)
    assert path.exists()

    loaded = load_snapshot(path)
    assert loaded == [{"item_code": "A", "rank": 1, "item_name": "商品"}, {"item_code": "B", "rank": 2, "item_name": "商品"}]


def test_load_snapshot_returns_none_when_missing(tmp_path):
    assert load_snapshot(tmp_path / "missing.json") is None
