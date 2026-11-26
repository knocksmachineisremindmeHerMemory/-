"""Amazonアソシエイトのリンク生成(楽天とは独立して動作する)。

ASINまたはキーワードからタグ付きリンクを作り、広告表記付きのMarkdownを出力する。
タグは --tag か環境変数 AMAZON_TAG で指定する。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from urllib.parse import quote

_ASIN_RE = re.compile(r"[A-Z0-9]{10}")
DISCLOSURE = "※本記事は広告(Amazonアソシエイト・プログラムのアフィリエイトリンク)を含みます。"


def get_tag(tag: str | None = None) -> str:
    t = (tag or os.environ.get("AMAZON_TAG", "")).strip()
    if not t:
        raise ValueError("トラッキングIDがありません。--tag か環境変数 AMAZON_TAG を設定してください。")
    return t


def product_url(asin: str, tag: str) -> str:
    if not _ASIN_RE.fullmatch(asin):
        raise ValueError(f"ASINの形式が不正です(英数字10桁): {asin!r}")
    return f"https://www.amazon.co.jp/dp/{asin}?tag={quote(tag)}"


def search_url(keyword: str, tag: str) -> str:
    kw = keyword.strip()
    if not kw:
        raise ValueError("キーワードが空です。")
    return f"https://www.amazon.co.jp/s?k={quote(kw)}&tag={quote(tag)}"


def build_block(title: str, url: str, label: str = "Amazonで見る", disclosure: bool = True) -> str:
    lines = [f"> **{title}**", ">", f"> [🛒 {label}]({url})"]
    if disclosure:
        lines += [">", f"> <sub>{DISCLOSURE}</sub>"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Amazonアソシエイトのリンクブロックを生成")
    p.add_argument("--asin", action="append", default=[], help="ASIN(複数指定可)")
    p.add_argument("--keyword", action="append", default=[], help="検索キーワード(複数指定可)")
    p.add_argument("--title", help="--asin 指定時の表示名(省略時はASIN)")
    p.add_argument("--tag", help="トラッキングID(省略時は AMAZON_TAG)")
    p.add_argument("--no-disclosure", action="store_true", help="広告表記を付けない")
    args = p.parse_args(argv)
    if not args.asin and not args.keyword:
        p.error("--asin か --keyword を指定してください。")
    try:
        tag = get_tag(args.tag)
        blocks = [
            build_block(args.title or a, product_url(a, tag), disclosure=not args.no_disclosure)
            for a in args.asin
        ] + [
            build_block(k, search_url(k, tag), "Amazonで探す", disclosure=not args.no_disclosure)
            for k in args.keyword
        ]
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
