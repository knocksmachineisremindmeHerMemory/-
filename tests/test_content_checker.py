import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from content_checker import check_text, load_config  # noqa: E402

CONFIG_PATH = Path(__file__).resolve().parent.parent / "src" / "ng_words.yaml"
CONFIG = load_config(CONFIG_PATH)


def test_check_text_detects_overclaim_word():
    findings = check_text("この商品は絶対に効果があります", CONFIG, platform="room")
    types = {f["type"] for f in findings}
    assert "overclaim" in types


def test_check_text_detects_missing_disclosure_on_threads():
    findings = check_text("この商品最高です #楽天ROOM", CONFIG, platform="threads")
    types = {f["type"] for f in findings}
    assert "disclosure_missing" in types


def test_check_text_passes_with_disclosure_on_threads():
    findings = check_text("この商品最高です #PR #楽天ROOM", CONFIG, platform="threads")
    types = {f["type"] for f in findings}
    assert "disclosure_missing" not in types


def test_check_text_does_not_require_disclosure_on_room():
    findings = check_text("この商品最高です", CONFIG, platform="room")
    types = {f["type"] for f in findings}
    assert "disclosure_missing" not in types


def test_check_text_detects_particle_repeat():
    findings = check_text("これはは良い商品です", CONFIG, platform="room")
    types = {f["type"] for f in findings}
    assert "typo" in types


def test_check_text_detects_length_over_limit():
    findings = check_text("あ" * 10, CONFIG, platform="room", max_length=5)
    types = {f["type"] for f in findings}
    assert "length" in types


def test_check_text_clean_text_has_no_findings():
    findings = check_text("使ってみて満足しています #PR #楽天ROOM", CONFIG, platform="threads", max_length=500)
    assert findings == []
