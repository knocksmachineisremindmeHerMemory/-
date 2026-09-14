import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import rakuten_api  # noqa: E402


@pytest.fixture(autouse=True)
def app_id_env(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "dummy-app-id")
    monkeypatch.delenv("RAKUTEN_AFFILIATE_ID", raising=False)


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_fetch_ranking_normalizes_items():
    fake_payload = {
        "Ranking": [
            {
                "rank": 1,
                "Item": {
                    "itemName": "人気商品",
                    "itemPrice": 2980,
                    "shopName": "ショップA",
                    "reviewCount": 50,
                    "reviewAverage": 4.2,
                    "pointRate": 1,
                    "itemUrl": "https://item.rakuten.co.jp/example/1/",
                    "mediumImageUrls": [{"imageUrl": "https://example.com/img.jpg"}],
                },
            }
        ]
    }

    with patch("rakuten_api.requests.get", return_value=FakeResponse(200, fake_payload)) as mock_get:
        items = rakuten_api.fetch_ranking(genre_id="100939", hits=10)

    assert mock_get.called
    assert len(items) == 1
    assert items[0]["item_name"] == "人気商品"
    assert items[0]["affiliate_url"] == "https://item.rakuten.co.jp/example/1/"


def test_fetch_ranking_raises_without_app_id(monkeypatch):
    monkeypatch.delenv("RAKUTEN_APP_ID", raising=False)
    with pytest.raises(rakuten_api.RakutenAPIError):
        rakuten_api.fetch_ranking()


def test_search_items_requires_keyword_or_genre():
    with pytest.raises(rakuten_api.RakutenAPIError):
        rakuten_api.search_items()


def test_fetch_ranking_raises_on_http_error():
    with patch("rakuten_api.requests.get", return_value=FakeResponse(403, "forbidden")):
        with pytest.raises(rakuten_api.RakutenAPIError):
            rakuten_api.fetch_ranking()
