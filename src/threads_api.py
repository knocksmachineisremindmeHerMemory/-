"""Threads API(Meta公式)のシンプルなクライアント。

テキスト投稿は「コンテナ作成 → 公開」の2段階で行う(Meta公式の仕様)。
認証情報(THREADS_USER_ID / THREADS_ACCESS_TOKEN)はMetaの開発者ポータルで
Threads APIプロダクトを有効化し、OAuth同意フローを経て取得する必要がある
(このスクリプトでは自動化できない、ユーザー自身の作業)。
"""
from __future__ import annotations

import os
import time

import requests

GRAPH_BASE = "https://graph.threads.net/v1.0"


class ThreadsAPIError(RuntimeError):
    pass


def get_credentials() -> tuple[str, str]:
    user_id = os.environ.get("THREADS_USER_ID", "").strip()
    access_token = os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
    if not user_id or not access_token:
        raise ThreadsAPIError(
            "THREADS_USER_ID / THREADS_ACCESS_TOKEN が設定されていません。"
            "Meta開発者ポータルでThreads APIを有効化し、.envに設定してください。"
        )
    return user_id, access_token


def create_text_container(text: str) -> str:
    """投稿用のコンテナを作成し、creation_idを返す。"""
    user_id, access_token = get_credentials()
    resp = requests.post(
        f"{GRAPH_BASE}/{user_id}/threads",
        data={"media_type": "TEXT", "text": text, "access_token": access_token},
        timeout=15,
    )
    if resp.status_code != 200:
        raise ThreadsAPIError(f"投稿コンテナの作成に失敗しました ({resp.status_code}): {resp.text}")

    data = resp.json()
    creation_id = data.get("id")
    if not creation_id:
        raise ThreadsAPIError(f"creation_idが取得できませんでした: {data}")
    return creation_id


def publish_container(creation_id: str) -> str:
    """作成済みのコンテナを公開し、投稿IDを返す。"""
    user_id, access_token = get_credentials()
    resp = requests.post(
        f"{GRAPH_BASE}/{user_id}/threads_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=15,
    )
    if resp.status_code != 200:
        raise ThreadsAPIError(f"投稿の公開に失敗しました ({resp.status_code}): {resp.text}")

    data = resp.json()
    post_id = data.get("id")
    if not post_id:
        raise ThreadsAPIError(f"post_idが取得できませんでした: {data}")
    return post_id


def post_text(text: str, publish_delay_seconds: int = 5) -> str:
    """テキストのみのThreads投稿を作成・公開し、投稿IDを返す。

    Meta公式の推奨により、コンテナ作成後は数秒待ってから公開する
    (作成直後は処理が完了していないことがあるため)。
    """
    creation_id = create_text_container(text)
    if publish_delay_seconds > 0:
        time.sleep(publish_delay_seconds)
    return publish_container(creation_id)
