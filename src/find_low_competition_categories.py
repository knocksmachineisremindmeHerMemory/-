"""競合が少なそうな商品ジャンルを比較するCLI。

楽天は「ジャンルごとのROOM投稿者数」のようなデータを公開していないため、
ジャンル内の総出品数とレビュー件数上位サンプルの平均レビュー数を参考値として
比較する(低いほど「強いレビュー実績を持つ定番商品が少ない」= 新規で目立ちやすい可能性、
というあくまでの目安)。

使い方:
    python src/find_low_competition_categories.py --genres コスメ,生活雑貨,キッチン用品
    python src/find_low_competition_categories.py --genres 100939,215783
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from category_competition import compare_genres, rank_by_low_competition  # noqa: E402
from main import resolve_genre_id  # noqa: E402
from rakuten_api import RakutenAPIError  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ジャンル別の競合(参考値)比較ツール")
    parser.add_argument("--genres", required=True, help="カンマ区切りのジャンル名またはジャンルID")
    parser.add_argument("--sample-size", type=int, default=30, help="各ジャンルで参照する上位サンプル件数")
    return parser


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")

    parser = build_parser()
    args = parser.parse_args()

    labels = [g.strip() for g in args.genres.split(",") if g.strip()]
    genre_map = {label: resolve_genre_id(label) for label in labels}

    try:
        stats_list = compare_genres(genre_map, sample_size=args.sample_size)
    except RakutenAPIError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    ranked = rank_by_low_competition(stats_list)

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"category_competition_{timestamp}.csv"
    md_path = OUTPUT_DIR / f"category_competition_{timestamp}.md"

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "genre_id", "total_item_count", "avg_review_count", "avg_price", "sample_size"])
        for s in ranked:
            writer.writerow(
                [s["label"], s["genre_id"], s["total_item_count"], round(s["avg_review_count"], 1), round(s["avg_price"], 0), s["sample_size"]]
            )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# ジャンル別 競合比較(参考値)\n\n")
        f.write(
            "※ROOM投稿者の実際の競合数は取得できないため、ジャンル内総出品数とレビュー件数上位の"
            "平均レビュー数を参考値として使用しています。数値が低いほど「まだレビュー実績の強い定番商品が"
            "少なく、新規でも目立ちやすい可能性がある」という目安です。\n\n"
        )
        f.write("| 順位 | ジャンル | 総出品数 | 上位平均レビュー数 | 上位平均価格 |\n|---|---|---:|---:|---:|\n")
        for i, s in enumerate(ranked, start=1):
            f.write(
                f"| {i} | {s['label']} | {s['total_item_count']} | {s['avg_review_count']:.1f} | ¥{s['avg_price']:,.0f} |\n"
            )

    print("競合比較(参考値)の結果:")
    for i, s in enumerate(ranked, start=1):
        print(f"  {i}. {s['label']}: 総出品数={s['total_item_count']}, 上位平均レビュー数={s['avg_review_count']:.1f}")
    print(f"CSV: {csv_path}")
    print(f"Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
