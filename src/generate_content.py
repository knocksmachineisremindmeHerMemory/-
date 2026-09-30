"""楽天ROOM/Threads向けのコンテンツ一式(紹介記事・投稿文)をまとめて生成するCLI。

商品リサーチ(ランキング or キーワード検索)→ ROOM投稿下書き・紹介記事・Threads投稿文を生成
→ 生成した全テキストをNGワード/表示義務チェックにかける、という一連の流れを1コマンドで行う。

使い方:
    python src/generate_content.py --mode ranking --genre コスメ --hits 10
    python src/generate_content.py --mode search --keyword "加湿器" --hits 10
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from article_generator import generate_article  # noqa: E402
from content_checker import check_text, load_config as load_ng_config  # noqa: E402
from draft_generator import generate_drafts  # noqa: E402
from keyword_suggester import suggest_keywords  # noqa: E402
from main import filter_items, resolve_genre_id  # noqa: E402
from rakuten_api import RakutenAPIError, fetch_ranking, search_items  # noqa: E402
from threads_generator import generate_threads_posts  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
NG_CONFIG_PATH = ROOT_DIR / "src" / "ng_words.yaml"
OUTPUT_DIR = ROOT_DIR / "output"

THREADS_MAX_LENGTH = 500


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ROOM/Threads向けコンテンツ一式の生成ツール")
    parser.add_argument("--mode", choices=["ranking", "search"], default="ranking")
    parser.add_argument("--genre", help="ジャンル名(src/genres.yaml参照) またはジャンルID")
    parser.add_argument("--keyword", help="検索キーワード (mode=search のとき使用)")
    parser.add_argument("--period", default="realtime", choices=["realtime", "daily", "weekly", "monthly"])
    parser.add_argument("--sort", default="-reviewCount")
    parser.add_argument("--hits", type=int, default=5, help="対象商品数(コンテンツを多数生成するため少なめ推奨)")
    parser.add_argument("--min-review-count", type=int, default=0)
    parser.add_argument("--min-review-average", type=float, default=0.0)
    parser.add_argument("--tags", help="カンマ区切りの追加ハッシュタグ")
    parser.add_argument(
        "--no-disclosure",
        action="store_true",
        help="Threads投稿に#PR等の開示表記を付けない(法令上のリスクを理解した上でのみ使用)",
    )
    return parser


def slugify(name: str, max_length: int = 30) -> str:
    slug = re.sub(r"[^\w\-]", "_", name)[:max_length]
    return slug or "item"


def main() -> int:
    from dotenv import load_dotenv

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
            items = search_items(keyword=args.keyword or "", genre_id=genre_id, sort=args.sort, hits=args.hits)
    except RakutenAPIError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    items = filter_items(items, args.min_review_count, args.min_review_average)
    if not items:
        print("条件に一致する商品が見つかりませんでした。")
        return 0

    ng_config = load_ng_config(NG_CONFIG_PATH)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_dir = OUTPUT_DIR / f"content_{timestamp}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    check_rows = []

    for i, item in enumerate(items, start=1):
        item_dir = bundle_dir / f"{i:02d}_{slugify(item['item_name'])}"
        item_dir.mkdir(parents=True, exist_ok=True)

        keywords = suggest_keywords(item, extra_text=" ".join(extra_tags or []))

        room_drafts = generate_drafts(item, extra_tags=extra_tags)
        room_text = "\n\n---\n\n".join(f"### {name}\n\n{text}" for name, text in room_drafts.items())
        (item_dir / "room_captions.md").write_text(room_text, encoding="utf-8")

        article_text = generate_article(item, keywords=keywords)
        (item_dir / "article.md").write_text(article_text, encoding="utf-8")

        threads_posts = generate_threads_posts(item, extra_tags=extra_tags, include_disclosure=not args.no_disclosure)
        threads_text = "\n\n---\n\n".join(f"### {name}\n\n{text}" for name, text in threads_posts.items())
        (item_dir / "threads_posts.md").write_text(threads_text, encoding="utf-8")

        keyword_text = f"名詞キーワード: {', '.join(keywords['nouns'])}\n検索フレーズ: {', '.join(keywords['search_phrases'])}\n"
        (item_dir / "keywords.txt").write_text(keyword_text, encoding="utf-8")

        for name, text in room_drafts.items():
            for finding in check_text(text, ng_config, platform="room"):
                check_rows.append({"item": item["item_name"], "content_type": f"room:{name}", **finding})

        for name, text in threads_posts.items():
            for finding in check_text(text, ng_config, platform="threads", max_length=THREADS_MAX_LENGTH):
                check_rows.append({"item": item["item_name"], "content_type": f"threads:{name}", **finding})

        for finding in check_text(article_text, ng_config, platform="article"):
            check_rows.append({"item": item["item_name"], "content_type": "article", **finding})

    check_csv_path = bundle_dir / "check_report.csv"
    with open(check_csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "content_type", "type", "message", "matched_text"])
        writer.writeheader()
        for row in check_rows:
            writer.writerow(row)

    print(f"{len(items)}件分のコンテンツを生成しました: {bundle_dir}")
    print(f"チェック結果: {len(check_rows)}件の指摘 → {check_csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
