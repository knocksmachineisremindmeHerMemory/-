"""Threads API(公式)への投稿CLI。

事前準備(このツールでは自動化できません。Metaの開発者ポータルで自分で行う必要があります):

1. https://developers.facebook.com/ でMeta Developerアプリを作成
2. アプリに「Threads API」プロダクトを追加し、Threadsアカウントを連携
3. OAuth同意フローで長期アクセストークンを取得する
   (スコープ: threads_basic, threads_content_publish)
4. 取得した値を .env に設定する:
   THREADS_USER_ID=...
   THREADS_ACCESS_TOKEN=...

安全のため、既定では実際には投稿しない「ドライラン」になっている。
実際に投稿するには --yes を明示する必要がある。

使い方:
    # ドライラン(内容とNGワードチェック結果だけ確認、実際には投稿しない)
    python src/post_to_threads.py --text "投稿したい本文"

    # generate_content.py が生成したファイルからパターンを指定して読み込む
    python src/post_to_threads.py --file output/content_xxx/01_商品/threads_posts.md --pattern empathy

    # 実際に投稿する
    python src/post_to_threads.py --text "投稿したい本文" --yes
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from content_checker import check_text, load_config as load_ng_config  # noqa: E402
from threads_api import ThreadsAPIError, post_text  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
NG_CONFIG_PATH = ROOT_DIR / "src" / "ng_words.yaml"
THREADS_MAX_LENGTH = 500


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Threads APIへの投稿ツール")
    parser.add_argument("--text", help="投稿する本文を直接指定")
    parser.add_argument("--file", help="generate_content.pyが生成したthreads_posts.mdのパス")
    parser.add_argument(
        "--pattern",
        default="empathy",
        choices=["empathy", "question", "problem_solution", "ranking"],
        help="--file指定時に使用するパターン名(デフォルト: empathy)",
    )
    parser.add_argument("--yes", action="store_true", help="実際に投稿する(指定しない場合はドライランのみ)")
    parser.add_argument(
        "--force", action="store_true", help="NGワード/開示チェックで問題が見つかっても投稿を強行する"
    )
    return parser


def extract_pattern(markdown_text: str, pattern: str) -> str | None:
    """generate_content.pyが出力するthreads_posts.md形式から、指定パターンの本文を取り出す。"""
    blocks = re.split(r"\n\n---\n\n", markdown_text.strip())
    for block in blocks:
        match = re.match(r"### (\w+)\n\n(.*)", block, re.DOTALL)
        if match and match.group(1) == pattern:
            return match.group(2).strip()
    return None


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")

    parser = build_parser()
    args = parser.parse_args()

    if args.text:
        text = args.text
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"エラー: ファイルが見つかりません: {file_path}", file=sys.stderr)
            return 1
        text = extract_pattern(file_path.read_text(encoding="utf-8"), args.pattern)
        if text is None:
            print(f"エラー: パターン「{args.pattern}」が見つかりませんでした。", file=sys.stderr)
            return 1
    else:
        print("--text か --file のどちらかを指定してください。", file=sys.stderr)
        return 1

    ng_config = load_ng_config(NG_CONFIG_PATH)
    findings = check_text(text, ng_config, platform="threads", max_length=THREADS_MAX_LENGTH)

    print("=== 投稿予定のテキスト ===")
    print(text)
    print(f"(文字数: {len(text)})\n")

    if findings:
        print("=== チェックで見つかった指摘 ===")
        for finding in findings:
            print(f"  - [{finding['type']}] {finding['message']}")
        if not args.force:
            print("\n上記の指摘があるため投稿を中止しました。内容を修正するか、--force で強行してください。")
            return 1
        print("\n--force が指定されているため、指摘を無視して続行します。")

    if not args.yes:
        print("ドライランのため実際には投稿していません。--yes を付けて再実行すると投稿されます。")
        return 0

    try:
        post_id = post_text(text)
    except ThreadsAPIError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    print(f"投稿しました。post_id={post_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
