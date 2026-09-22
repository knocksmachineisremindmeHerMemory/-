"""楽天ROOM 商品リサーチ & 投稿下書き生成CLI。

使い方の例:
    python src/main.py --mode ranking --genre コスメ --hits 10
    python src/main.py --mode search --keyword "加湿器" --sort -reviewCount --hits 10

出力: output/drafts_YYYYMMDD_HHMMSS.csv と .md
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from draft_generator import build_affiliate_block, generate_drafts  # noqa: E402
from rakuten_api import RakutenAPIError, fetch_ranking, search_items  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
GENRES_FILE = ROOT_DIR / "src" / "genres.yaml"
OUTPUT_DIR = ROOT_DIR / "output"


def load_genre_map() -> dict[str, str]:
    if not GENRES_FILE.exists():
        return {}
    with open(GENRES_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_genre_id(genre_arg: str | None) -> str:
    if not genre_arg:
        return "0"
    genre_map = load_genre_map()
    return genre_map.get(genre_arg, genre_arg)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="楽天ROOM 商品リサーチ & 下書き生成ツール")
    parser.add_argument("--mode", choices=["ranking", "search"], default="ranking")
    parser.add_argument("--genre", help="ジャンル名(src/genres.yaml参照) またはジャンルID")
    parser.add_argument("--keyword", help="検索キーワード (mode=search のとき使用)")
    parser.add_argument("--period", default="realtime", choices=["realtime", "daily", "weekly", "monthly"])
    parser.add_argument("--sort", default="-reviewCount", help="mode=search のときの並び順")
    parser.add_argument("--min-price", type=int, default=None)
    parser.add_argument("--max-price", type=int, default=None)
    parser.add_argument("--hits", type=int, default=10, help="取得する商品数")
    parser.add_argument("--min-review-count", type=int, default=0, help="このレビュー件数未満の商品は除外")
    parser.add_argument("--min-review-average", type=float, default=0.0, help="この評価未満の商品は除外")
    parser.add_argument("--tags", help="カンマ区切りの追加ハッシュタグ (例: 加湿器,冬支度)")
    parser.add_argument(
        "--asin",
        help="Amazon併記ブロックに使うASIN。全取得商品に同じASINが適用されるため、"
        "--hits 1 など単一商品を取得する場合のみ指定してください。",
    )
    parser.add_argument(
        "--amazon-tag",
        help="Amazonアソシエイトのトラッキングタグ (省略時は環境変数 AMAZON_TAG を使用)",
    )
    return parser


def filter_items(items: list[dict], min_review_count: int, min_review_average: float) -> list[dict]:
    filtered = []
    for item in items:
        if item.get("review_count", 0) < min_review_count:
            continue
        if item.get("review_average", 0) < min_review_average:
            continue
        filtered.append(item)
    return filtered


def write_outputs(rows: list[dict]) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"drafts_{timestamp}.csv"
    md_path = OUTPUT_DIR / f"drafts_{timestamp}.md"

    fieldnames = [
        "rank", "item_name", "item_price", "review_average", "review_count",
        "affiliate_url", "draft_review", "draft_sale", "draft_simple", "draft_recommend",
        "draft_affiliate_block",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 楽天ROOM 投稿下書き候補\n\n")
        for row in rows:
            f.write(f"## {row['item_name']} ({row['item_price']}円)\n\n")
            f.write(f"- レビュー: {row['review_average']} ({row['review_count']}件)\n")
            f.write(f"- リンク: {row['affiliate_url']}\n\n")
            for key, label in [
                ("draft_review", "レビュー訴求"),
                ("draft_sale", "セール訴求"),
                ("draft_simple", "シンプル紹介"),
                ("draft_recommend", "おすすめ訴求"),
            ]:
                f.write(f"**{label}**\n\n")
                f.write(f"```\n{row[key]}\n```\n\n")
            f.write("**Amazon併記ブロック(コピペ用)**\n\n")
            f.write(f"{row['draft_affiliate_block']}\n\n")

    return csv_path, md_path


def main() -> int:
    load_dotenv(ROOT_DIR / ".env")
    parser = build_parser()
    args = parser.parse_args()

    extra_tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    try:
        if args.mode == "ranking":
            genre_id = resolve_genre_id(args.genre)
            items = fetch_ranking(genre_id=genre_id, period=args.period, hits=args.hits)
        else:
            if not args.keyword and not args.genre:
                print("mode=search では --keyword か --genre のどちらかを指定してください。", file=sys.stderr)
                return 1
            genre_id = resolve_genre_id(args.genre) if args.genre else ""
            items = search_items(
                keyword=args.keyword or "",
                genre_id=genre_id,
                sort=args.sort,
                min_price=args.min_price,
                max_price=args.max_price,
                hits=args.hits,
            )
    except RakutenAPIError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    items = filter_items(items, args.min_review_count, args.min_review_average)
    if not items:
        print("条件に一致する商品が見つかりませんでした。フィルタ条件を緩めてみてください。")
        return 0

    rows = []
    for item in items:
        drafts = generate_drafts(item, extra_tags=extra_tags)
        affiliate_block = build_affiliate_block(item, asin=args.asin, amazon_tag=args.amazon_tag)
        rows.append(
            {
                "rank": item.get("rank"),
                "item_name": item.get("item_name"),
                "item_price": item.get("item_price"),
                "review_average": item.get("review_average"),
                "review_count": item.get("review_count"),
                "affiliate_url": item.get("affiliate_url"),
                "draft_review": drafts["review"],
                "draft_sale": drafts["sale"],
                "draft_simple": drafts["simple"],
                "draft_recommend": drafts["recommend"],
                "draft_affiliate_block": affiliate_block,
            }
        )

    csv_path, md_path = write_outputs(rows)
    print(f"{len(rows)}件の下書きを生成しました。")
    print(f"CSV: {csv_path}")
    print(f"Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
