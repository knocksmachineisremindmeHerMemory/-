import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import post_to_threads  # noqa: E402

SAMPLE_MD = """### empathy

最近これ使ってるけど良い感じ #PR #楽天ROOM

---

### question

気になってる人いる?😳 #PR #楽天ROOM
"""


def test_extract_pattern_returns_matching_block():
    text = post_to_threads.extract_pattern(SAMPLE_MD, "question")
    assert text == "気になってる人いる?😳 #PR #楽天ROOM"


def test_extract_pattern_returns_none_when_missing():
    assert post_to_threads.extract_pattern(SAMPLE_MD, "ranking") is None


def test_main_dry_run_does_not_call_api(capsys):
    sys.argv = ["post_to_threads.py", "--text", "テスト投稿 #PR #楽天ROOM"]
    with patch("post_to_threads.post_text") as mock_post:
        exit_code = post_to_threads.main()

    assert exit_code == 0
    assert not mock_post.called
    captured = capsys.readouterr()
    assert "ドライラン" in captured.out


def test_main_blocks_on_ng_findings_without_force(capsys):
    sys.argv = ["post_to_threads.py", "--text", "これは絶対に効果があります", "--yes"]
    with patch("post_to_threads.post_text") as mock_post:
        exit_code = post_to_threads.main()

    assert exit_code == 1
    assert not mock_post.called
    captured = capsys.readouterr()
    assert "指摘があるため投稿を中止" in captured.out


def test_main_posts_when_yes_and_force_given(capsys):
    sys.argv = ["post_to_threads.py", "--text", "これは絶対に効果があります", "--yes", "--force"]
    with patch("post_to_threads.post_text", return_value="post-123") as mock_post:
        exit_code = post_to_threads.main()

    assert exit_code == 0
    assert mock_post.called
    captured = capsys.readouterr()
    assert "post-123" in captured.out


def test_main_posts_clean_text_with_yes(capsys):
    sys.argv = ["post_to_threads.py", "--text", "使ってみて満足しています #PR #楽天ROOM", "--yes"]
    with patch("post_to_threads.post_text", return_value="post-456") as mock_post:
        exit_code = post_to_threads.main()

    assert exit_code == 0
    assert mock_post.called
    captured = capsys.readouterr()
    assert "post-456" in captured.out
