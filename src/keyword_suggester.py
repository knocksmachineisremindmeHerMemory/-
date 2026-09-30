"""商品情報から検索されそうなキーワード・検索フレーズを抽出する。

janome(純Python・追加のシステム依存なしの形態素解析器)で商品名・キャッチコピーから
名詞を抽出し、よくある検索補助語と組み合わせて検索フレーズ候補を作る。
"""
from __future__ import annotations

from janome.tokenizer import Tokenizer

_tokenizer = Tokenizer()

_SEARCH_MODIFIERS = ["レビュー", "口コミ", "おすすめ", "人気", "比較", "使い方", "安い"]

_STOPWORDS = {"こと", "もの", "ため", "これ", "それ", "とき", "よう"}


def extract_nouns(text: str, min_length: int = 2) -> list[str]:
    """テキストから名詞を抽出する(出現順・重複なし)。"""
    seen: list[str] = []
    for token in _tokenizer.tokenize(text):
        pos = token.part_of_speech.split(",")[0]
        surface = token.surface
        if pos != "名詞":
            continue
        if len(surface) < min_length or surface in _STOPWORDS:
            continue
        if surface not in seen:
            seen.append(surface)
    return seen


def suggest_keywords(item: dict, extra_text: str = "", top_n: int = 8) -> dict[str, list[str]]:
    """商品の名詞キーワードと、検索フレーズ候補を返す。"""
    text = f"{item.get('item_name', '')} {item.get('catch_copy', '')} {extra_text}".strip()
    nouns = extract_nouns(text)[:top_n]

    search_phrases = []
    if nouns:
        primary = nouns[0]
        search_phrases = [f"{primary} {modifier}" for modifier in _SEARCH_MODIFIERS]

    return {"nouns": nouns, "search_phrases": search_phrases}
