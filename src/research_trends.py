"""楽天ランキングの「伸びている商品」検出 + 検索キーワード出しCLI。

前回実行時のスナップショットと比較し、順位が急上昇した商品・新規ランクインした商品を
抽出する。初回実行時は比較対象が無いため、その回のランキングをそのまま保存するだけになる
(2回目以降の実行から変動が分かる)。

使い方:
    python src/research_trends.py --genre コスメ --hits 30
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from keyword_suggester import suggest_keywords  # noqa: E402
from main import resolve_genre_id  # noqa: E402
from rakuten_api import RakutenAPIError, fetch_ranking  # noqa: E402
from ranking_tracker import compute_rank_changes, filter_growing, load_snapshot, save_snapshot  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT_DIR / "data" / "ranking_snapshots"
OUTPUT_DIR = ROOT_DIR / "output"

_STATUS_LABELS = {
    "new_entry": "新規ランクイン",
    "rising": "急上昇",
    "falling": "下落",
    "stable": "変動なし",
    "unknown": "初回実行(比較対象なし)",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="楽天ランキングの伸びている商品を検出し、検索キーワードを提案する")
    parser.add_argument("--genre", required=True, help="ジャンル名(src/genres.yaml参照) またはジャンルID")
    parser.add_argument("--period", default="realtime", choices=["realtime", "daily", "weekly", "monthly"])
    parser.add_argument("--hits", type=int, default=30, help="取得する商品数")
    parser.add_argument("--rising-threshold", type=int, default=5, help="この順位以上上昇したら「急上昇」とみなす")
    return parser


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")

    parser = build_parser()
    args = parser.parse_args()
    genre_id = resolve_genre_id(args.genre)

    try:
        current_items = fetch_ranking(genre_id=genre_id, period=args.period, hits=args.hits)
    except RakutenAPIError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    if not current_items:
        print("ランキングデータが取得できませんでした。")
        return 0

    snapshot_path = SNAPSHOT_DIR / f"{genre_id}.json"
    previous_items = load_snapshot(snapshot_path)
    changes = compute_rank_changes(previous_items, current_items, rising_threshold=args.rising_threshold)
    save_snapshot(snapshot_path, current_items)

    growing = filter_growing(changes)

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"trend_research_{timestamp}.csv"
    md_path = OUTPUT_DIR / f"trend_research_{timestamp}.md"

    fieldnames = [
        "status", "rank", "previous_rank", "rank_change", "item_name", "item_price",
        "review_count", "affiliate_url", "keywords", "search_phrases",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in growing:
            kw = suggest_keywords(item)
            writer.writerow(
                {
                    "status": _STATUS_LABELS.get(item["status"], item["status"]),
                    "rank": item["rank"],
                    "previous_rank": item["previous_rank"],
                    "rank_change": item["rank_change"],
                    "item_name": item["item_name"],
                    "item_price": item["item_price"],
                    "review_count": item["review_count"],
                    "affiliate_url": item["affiliate_url"],
                    "keywords": ", ".join(kw["nouns"]),
                    "search_phrases": ", ".join(kw["search_phrases"]),
                }
            )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 伸びている商品レポート ({args.genre}, {args.period})\n\n")
        if previous_items is None:
            f.write(
                "※今回が初回実行のため、順位変動は分かりません。次回以降の実行から比較できます。\n\n"
            )
        if not growing:
            f.write("今回、急上昇・新規ランクインした商品はありませんでした。\n")
        for item in growing:
            kw = suggest_keywords(item)
            f.write(f"## {item['item_name']}\n\n")
            f.write(f"- 状態: {_STATUS_LABELS.get(item['status'], item['status'])}\n")
            f.write(f"- 順位: {item['previous_rank']} → {item['rank']}\n")
            f.write(f"- 価格: {item['item_price']}円 / レビュー: {item['review_count']}件\n")
            f.write(f"- リンク: {item['affiliate_url']}\n")
            f.write(f"- キーワード候補: {', '.join(kw['nouns'])}\n")
            f.write(f"- 検索フレーズ候補: {', '.join(kw['search_phrases'])}\n\n")

    print(f"{len(growing)}件の伸びている商品を検出しました({len(current_items)}件中)。")
    print(f"CSV: {csv_path}")
    print(f"Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
