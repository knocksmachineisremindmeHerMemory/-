import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from keyword_suggester import extract_nouns, suggest_keywords  # noqa: E402


def test_extract_nouns_finds_key_terms():
    nouns = extract_nouns("超音波式アロマ加湿器はリビングにおすすめの人気アイテムです")
    assert "加湿" in nouns
    assert "リビング" in nouns


def test_suggest_keywords_builds_search_phrases():
    item = {"item_name": "超音波式アロマ加湿器", "catch_copy": "リビングにおすすめ"}
    result = suggest_keywords(item, top_n=5)

    assert "nouns" in result
    assert "search_phrases" in result
    assert len(result["nouns"]) > 0
    assert any("レビュー" in phrase for phrase in result["search_phrases"])


def test_suggest_keywords_handles_empty_item():
    result = suggest_keywords({})
    assert result["nouns"] == []
    assert result["search_phrases"] == []
