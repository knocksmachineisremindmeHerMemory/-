"""楽天ROOM収益化ツール群 統合CLIエントリポイント。

商品リサーチ・成果トラッキング・投稿カレンダー生成の3ツールを、
サブコマンド経由でひとつのエントリポイントから実行できるようにする。
各ツールは従来どおり src/main.py 等を直接実行しても動作する。

使い方の例:
    python src/cli.py research --mode ranking --genre コスメ --hits 10
    python src/cli.py track --csv path/to/report.csv --period month
    python src/cli.py calendar --days 30

各サブコマンドの詳細なオプションは `python src/cli.py <サブコマンド> --help` を参照。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import generate_calendar  # noqa: E402
import main as research  # noqa: E402
import track_performance  # noqa: E402

COMMANDS = {
    "research": ("商品リサーチ & 投稿下書き生成", research.main),
    "track": ("成果トラッキング & ダッシュボード生成", track_performance.main),
    "calendar": ("投稿カレンダー & リマインド生成", generate_calendar.main),
}


def print_usage() -> None:
    print("使い方: python src/cli.py <サブコマンド> [オプション]\n")
    print("サブコマンド:")
    for name, (description, _) in COMMANDS.items():
        print(f"  {name:<10} {description}")
    print("\n各サブコマンドのオプション一覧: python src/cli.py <サブコマンド> --help")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    if not argv:
        print_usage()
        return 1

    if argv[0] in ("-h", "--help"):
        print_usage()
        return 0

    command, rest = argv[0], argv[1:]
    if command not in COMMANDS:
        print(f"エラー: 不明なサブコマンドです: {command}", file=sys.stderr)
        print_usage()
        return 1

    _, run = COMMANDS[command]
    return run(rest)


if __name__ == "__main__":
    raise SystemExit(main())
