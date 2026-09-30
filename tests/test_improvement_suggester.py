import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from improvement_suggester import build_suggestions  # noqa: E402


def _base_summary(**overrides):
    summary = {
        "total_reward": 1000,
        "total_sales": 10000,
        "total_records": 10,
        "by_period": [],
        "top_products": [{"product_name": "商品A", "reward_amount": 300, "count": 5}],
        "status_breakdown": {"承認": 8, "未承認": 1, "否認": 1},
        "latest_vs_previous_pct": None,
    }
    summary.update(overrides)
    return summary


def test_suggests_action_on_large_decline():
    summary = _base_summary(latest_vs_previous_pct=-35.0)
    suggestions = build_suggestions(summary)
    assert any("減少" in s for s in suggestions)


def test_suggests_action_on_large_growth():
    summary = _base_summary(latest_vs_previous_pct=42.0)
    suggestions = build_suggestions(summary)
    assert any("増加" in s for s in suggestions)


def test_suggests_reviewing_denial_rate_when_high():
    summary = _base_summary(status_breakdown={"承認": 5, "未承認": 0, "否認": 5})
    suggestions = build_suggestions(summary)
    assert any("否認率" in s for s in suggestions)


def test_suggests_diversification_on_high_concentration():
    summary = _base_summary(
        total_reward=1000,
        top_products=[{"product_name": "商品A", "reward_amount": 600, "count": 3}],
    )
    suggestions = build_suggestions(summary)
    assert any("商品A" in s and "依存度" in s for s in suggestions)


def test_returns_default_message_when_nothing_notable():
    summary = _base_summary(
        latest_vs_previous_pct=1.0,
        status_breakdown={"承認": 10},
        top_products=[{"product_name": "商品A", "reward_amount": 100, "count": 3}],
    )
    suggestions = build_suggestions(summary)
    assert suggestions == ["特に大きな懸念点は見当たりません。現在の投稿頻度・商品選定を継続してください。"]
