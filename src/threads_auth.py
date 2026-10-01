"""Threads APIのOAuth認証コードを、長期アクセストークンに交換するヘルパー。

Meta Developerアプリの作成・OAuth同意画面での承認はブラウザでの手動操作が必要
(このスクリプトでは自動化できない)。認可後に得られる`code`をもとに、
以下の2段階でトークンを取得するAPI呼び出しだけを自動化する:

1. 認証コード → 短期アクセストークン
2. 短期アクセストークン → 長期アクセストークン(60日間有効)

使い方:
    python src/threads_auth.py \
        --client-id <METAアプリのThreads App ID> \
        --client-secret <METAアプリのThreads App Secret> \
        --redirect-uri <認証時に設定したリダイレクトURI> \
        --code <認証後にリダイレクト先URLのcodeパラメータから取得した値>

出力された THREADS_USER_ID / THREADS_ACCESS_TOKEN を .env に設定してください。
"""
from __future__ import annotations

import argparse
import sys

import requests

TOKEN_ENDPOINT = "https://graph.threads.net/oauth/access_token"
EXCHANGE_ENDPOINT = "https://graph.threads.net/access_token"
ME_ENDPOINT = "https://graph.threads.net/v1.0/me"


class ThreadsAuthError(RuntimeError):
    pass


def exchange_code_for_short_lived_token(
    client_id: str, client_secret: str, redirect_uri: str, code: str
) -> tuple[str, str]:
    """認証コードを短期アクセストークンに交換する。(access_token, user_id) を返す。"""
    resp = requests.post(
        TOKEN_ENDPOINT,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise ThreadsAuthError(f"短期アクセストークンの取得に失敗しました ({resp.status_code}): {resp.text}")

    data = resp.json()
    access_token = data.get("access_token")
    user_id = data.get("user_id")
    if not access_token or not user_id:
        raise ThreadsAuthError(f"access_token/user_idが取得できませんでした: {data}")
    return access_token, str(user_id)


def exchange_for_long_lived_token(client_secret: str, short_lived_token: str) -> str:
    """短期アクセストークンを長期アクセストークン(60日間有効)に交換する。"""
    resp = requests.get(
        EXCHANGE_ENDPOINT,
        params={
            "grant_type": "th_exchange_token",
            "client_secret": client_secret,
            "access_token": short_lived_token,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise ThreadsAuthError(f"長期アクセストークンの取得に失敗しました ({resp.status_code}): {resp.text}")

    data = resp.json()
    access_token = data.get("access_token")
    if not access_token:
        raise ThreadsAuthError(f"access_tokenが取得できませんでした: {data}")
    return access_token


def fetch_username(user_id: str, access_token: str) -> str | None:
    """確認用にThreadsのユーザー名を取得する(失敗しても致命的ではない)。"""
    resp = requests.get(
        ME_ENDPOINT,
        params={"fields": "id,username", "access_token": access_token},
        timeout=15,
    )
    if resp.status_code != 200:
        return None
    return resp.json().get("username")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Threads APIの認証コードを長期アクセストークンに交換する")
    parser.add_argument("--client-id", required=True, help="MetaアプリのThreads App ID")
    parser.add_argument("--client-secret", required=True, help="MetaアプリのThreads App Secret")
    parser.add_argument("--redirect-uri", required=True, help="認証時に設定したリダイレクトURI")
    parser.add_argument("--code", required=True, help="リダイレクト先URLのcodeパラメータの値")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        short_lived_token, user_id = exchange_code_for_short_lived_token(
            args.client_id, args.client_secret, args.redirect_uri, args.code
        )
        long_lived_token = exchange_for_long_lived_token(args.client_secret, short_lived_token)
    except ThreadsAuthError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    username = fetch_username(user_id, long_lived_token)

    print("取得に成功しました。以下を .env に設定してください(60日間有効、期限が近づいたら再取得が必要です):\n")
    print(f"THREADS_USER_ID={user_id}")
    print(f"THREADS_ACCESS_TOKEN={long_lived_token}")
    if username:
        print(f"\n(アカウント確認: @{username})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
