"""投稿文の誤字・NGワード・表示義務(ステマ規制対応)を簡易チェックする。

完全な日本語スペルチェックは行わない(そのためには本格的な形態素解析・辞書照合が必要で
このツール群の範囲を超える)。代わりに実務上リスクの大きい3点に絞って検出する:

1. 誇大・薬機法/景品表示法上リスクのある表現(NGワードリストとの一致)
2. 助詞の連続などの単純な誤字パターン
3. 広告・アフィリエイトである旨の明示漏れ(2023年施行のステマ規制対応)
"""
from __future__ import annotations

import re
from typing import Any

import yaml


def load_config(path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_text(
    text: str,
    config: dict[str, Any],
    platform: str = "threads",
    max_length: int | None = None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for word in config.get("overclaim", []) or []:
        if word in text:
            findings.append(
                {
                    "type": "overclaim",
                    "message": f"誇大・薬機法/景品表示法上リスクのある表現の可能性: 「{word}」",
                    "matched_text": word,
                }
            )

    for particle in config.get("particle_repeat_check", []) or []:
        if particle * 2 in text:
            findings.append(
                {
                    "type": "typo",
                    "message": f"助詞「{particle}」が連続しています。誤字の可能性があります。",
                    "matched_text": particle * 2,
                }
            )

    for match in re.finditer(r"[!!?？]{3,}", text):
        findings.append(
            {
                "type": "style",
                "message": f"感嘆符・疑問符の連続使用が目立ちます: 「{match.group()}」",
                "matched_text": match.group(),
            }
        )

    if platform in (config.get("disclosure_required_platforms") or []):
        disclosure_keywords = config.get("disclosure_keywords", []) or []
        if not any(kw.lower() in text.lower() for kw in disclosure_keywords):
            findings.append(
                {
                    "type": "disclosure_missing",
                    "message": (
                        "広告・アフィリエイトである旨の明示(例: #PR)が見つかりません。"
                        "景品表示法のステマ規制(2023年施行)に注意してください。"
                    ),
                    "matched_text": None,
                }
            )

    if max_length is not None and len(text) > max_length:
        findings.append(
            {
                "type": "length",
                "message": f"文字数が上限({max_length}字)を超えています(現在{len(text)}字)。",
                "matched_text": None,
            }
        )

    return findings
