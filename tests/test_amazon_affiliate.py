import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import amazon_affiliate as aa  # noqa: E402


def test_product_url():
    assert aa.product_url("B0TESTASIN", "t-22") == "https://www.amazon.co.jp/dp/B0TESTASIN?tag=t-22"


def test_invalid_asin():
    with pytest.raises(ValueError):
        aa.product_url("bad", "t-22")


def test_search_url_encodes():
    assert aa.search_url("加湿器", "t-22").endswith("&tag=t-22")
    assert "%E5%8A%A0" in aa.search_url("加湿器", "t-22")


def test_tag_required(monkeypatch):
    monkeypatch.delenv("AMAZON_TAG", raising=False)
    with pytest.raises(ValueError):
        aa.get_tag(None)


def test_cli_outputs_disclosure(capsys, monkeypatch):
    monkeypatch.setenv("AMAZON_TAG", "t-22")
    assert aa.main(["--asin", "B0TESTASIN", "--title", "商品"]) == 0
    out = capsys.readouterr().out
    assert "dp/B0TESTASIN?tag=t-22" in out and "広告" in out
