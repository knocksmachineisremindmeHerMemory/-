"""楽天市場APIのシンプルなクライアント。

商品ランキングAPI / 商品検索APIを呼び出し、商品情報を扱いやすい辞書のリストに正規化する。
"""
from __future__ import annotations

import os
from typing import Any

import requests

RANKING_ENDPOINT = "https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20220601"
# 商品検索APIは2026-07-01版(ichibams)。旧版(app.rakuten.co.jp)はaccessKey不要だったが、
# 新版はapplicationIdに加えてaccessKeyが必須になっている。
SEARCH_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"


class RakutenAPIError(RuntimeError):
    pass


def _get_app_id() -> str:
    app_id = os.environ.get("RAKUTEN_APP_ID", "").strip()
    if not app_id:
        raise RakutenAPIError(
            "RAKUTEN_APP_ID が設定されていません。.env に楽天デベロッパーズのアプリIDを設定してください。"
        )
    return app_id


def _get_access_key() -> str:
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
    if not access_key:
        raise RakutenAPIError(
            "RAKUTEN_ACCESS_KEY が設定されていません。"
            "商品検索API(2026-07-01版)ではapplicationIdに加えてアクセスキーが必須です。"
            ".env に楽天デベロッパーズのアクセスキーを設定してください。"
        )
    return access_key


def _normalize_item(raw_item: dict[str, Any], rank: int | None = None) -> dict[str, Any]:
    images = raw_item.get("mediumImageUrls") or []
    image_url = ""
    if images:
        image_url = images[0].get("imageUrl", "") if isinstance(images[0], dict) else images[0]

    return {
        "rank": rank,
        "item_name": raw_item.get("itemName", ""),
        "item_price": raw_item.get("itemPrice", ""),
        "shop_name": raw_item.get("shopName", ""),
        "review_count": raw_item.get("reviewCount", 0),
        "review_average": raw_item.get("reviewAverage", 0),
        "point_rate": raw_item.get("pointRate", 1),
        "item_url": raw_item.get("itemUrl", ""),
        "affiliate_url": raw_item.get("affiliateUrl", "") or raw_item.get("itemUrl", ""),
        "image_url": image_url,
        "genre_id": raw_item.get("genreId", ""),
        "catch_copy": raw_item.get("catchcopy", ""),
    }


def fetch_ranking(
    genre_id: str = "0",
    period: str = "realtime",
    hits: int = 20,
) -> list[dict[str, Any]]:
    """ジャンル別の売れ筋ランキングを取得する。

    period: realtime / daily / weekly / monthly
    """
    params = {
        "applicationId": _get_app_id(),
        "genreId": genre_id,
        "period": period,
        "format": "json",
    }
    affiliate_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
    if affiliate_id:
        params["affiliateId"] = affiliate_id

    resp = requests.get(RANKING_ENDPOINT, params=params, timeout=15)
    if resp.status_code != 200:
        raise RakutenAPIError(f"ランキングAPI呼び出しに失敗しました ({resp.status_code}): {resp.text}")

    data = resp.json()
    ranking = data.get("Ranking", [])
    items = []
    for entry in ranking[:hits]:
        raw_item = entry.get("Item", {})
        items.append(_normalize_item(raw_item, rank=entry.get("rank")))
    return items


def search_items(
    keyword: str = "",
    genre_id: str = "",
    sort: str = "-reviewCount",
    min_price: int | None = None,
    max_price: int | None = None,
    hits: int = 20,
) -> list[dict[str, Any]]:
    """キーワード・ジャンルで商品を検索する。

    sort例: standard(標準) / -reviewCount(レビュー件数順) / -reviewAverage(評価順) / +itemPrice(価格が安い順)
    """
    if not keyword and not genre_id:
        raise RakutenAPIError("keyword か genre_id のどちらかを指定してください。")

    params: dict[str, Any] = {
        "applicationId": _get_app_id(),
        "accessKey": _get_access_key(),
        "sort": sort,
        "hits": min(hits, 30),
        "format": "json",
    }
    if keyword:
        params["keyword"] = keyword
    if genre_id:
        params["genreId"] = genre_id
    if min_price is not None:
        params["minPrice"] = min_price
    if max_price is not None:
        params["maxPrice"] = max_price

    affiliate_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
    if affiliate_id:
        params["affiliateId"] = affiliate_id

    resp = requests.get(SEARCH_ENDPOINT, params=params, timeout=15)
    if resp.status_code != 200:
        raise RakutenAPIError(f"検索API呼び出しに失敗しました ({resp.status_code}): {resp.text}")

    data = resp.json()
    raw_items = data.get("Items", [])
    items = []
    for i, entry in enumerate(raw_items, start=1):
        raw_item = entry.get("Item", entry)
        items.append(_normalize_item(raw_item, rank=i))
    return items
