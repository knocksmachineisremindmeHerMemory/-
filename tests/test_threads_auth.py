import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import threads_auth  # noqa: E402


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_exchange_code_for_short_lived_token_success():
    with patch(
        "threads_auth.requests.post",
        return_value=FakeResponse(200, {"access_token": "short-token", "user_id": "999"}),
    ):
        token, user_id = threads_auth.exchange_code_for_short_lived_token(
            "client-id", "client-secret", "https://example.com/callback", "auth-code"
        )

    assert token == "short-token"
    assert user_id == "999"


def test_exchange_code_for_short_lived_token_raises_on_error():
    with patch("threads_auth.requests.post", return_value=FakeResponse(400, "invalid code")):
        with pytest.raises(threads_auth.ThreadsAuthError):
            threads_auth.exchange_code_for_short_lived_token("id", "secret", "uri", "bad-code")


def test_exchange_for_long_lived_token_success():
    with patch(
        "threads_auth.requests.get",
        return_value=FakeResponse(200, {"access_token": "long-token", "expires_in": 5184000}),
    ):
        token = threads_auth.exchange_for_long_lived_token("client-secret", "short-token")

    assert token == "long-token"


def test_exchange_for_long_lived_token_raises_on_error():
    with patch("threads_auth.requests.get", return_value=FakeResponse(400, "invalid token")):
        with pytest.raises(threads_auth.ThreadsAuthError):
            threads_auth.exchange_for_long_lived_token("secret", "bad-token")


def test_fetch_username_returns_none_on_error():
    with patch("threads_auth.requests.get", return_value=FakeResponse(400, "error")):
        assert threads_auth.fetch_username("999", "token") is None


def test_fetch_username_returns_value_on_success():
    with patch("threads_auth.requests.get", return_value=FakeResponse(200, {"id": "999", "username": "testuser"})):
        assert threads_auth.fetch_username("999", "token") == "testuser"


def test_main_prints_tokens_on_success(capsys):
    sys.argv = [
        "threads_auth.py",
        "--client-id", "client-id",
        "--client-secret", "client-secret",
        "--redirect-uri", "https://example.com/callback",
        "--code", "auth-code",
    ]
    with patch("threads_auth.requests.post", return_value=FakeResponse(200, {"access_token": "short", "user_id": "999"})), \
         patch("threads_auth.requests.get", side_effect=[
             FakeResponse(200, {"access_token": "long-lived-token"}),
             FakeResponse(200, {"id": "999", "username": "testuser"}),
         ]):
        exit_code = threads_auth.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "THREADS_USER_ID=999" in captured.out
    assert "THREADS_ACCESS_TOKEN=long-lived-token" in captured.out
    assert "@testuser" in captured.out
