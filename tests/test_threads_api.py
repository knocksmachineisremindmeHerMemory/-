import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import threads_api  # noqa: E402


@pytest.fixture(autouse=True)
def credentials_env(monkeypatch):
    monkeypatch.setenv("THREADS_USER_ID", "12345")
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "dummy-token")


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_create_text_container_returns_creation_id():
    with patch("threads_api.requests.post", return_value=FakeResponse(200, {"id": "container-1"})) as mock_post:
        creation_id = threads_api.create_text_container("こんにちは")

    assert creation_id == "container-1"
    assert mock_post.called
    _, kwargs = mock_post.call_args
    assert kwargs["data"]["media_type"] == "TEXT"
    assert kwargs["data"]["text"] == "こんにちは"


def test_create_text_container_raises_on_http_error():
    with patch("threads_api.requests.post", return_value=FakeResponse(400, "bad request")):
        with pytest.raises(threads_api.ThreadsAPIError):
            threads_api.create_text_container("こんにちは")


def test_create_text_container_raises_when_id_missing():
    with patch("threads_api.requests.post", return_value=FakeResponse(200, {})):
        with pytest.raises(threads_api.ThreadsAPIError):
            threads_api.create_text_container("こんにちは")


def test_publish_container_returns_post_id():
    with patch("threads_api.requests.post", return_value=FakeResponse(200, {"id": "post-1"})):
        post_id = threads_api.publish_container("container-1")

    assert post_id == "post-1"


def test_post_text_creates_then_publishes():
    responses = [FakeResponse(200, {"id": "container-1"}), FakeResponse(200, {"id": "post-1"})]
    with patch("threads_api.requests.post", side_effect=responses):
        post_id = threads_api.post_text("こんにちは", publish_delay_seconds=0)

    assert post_id == "post-1"


def test_get_credentials_raises_when_missing(monkeypatch):
    monkeypatch.delenv("THREADS_USER_ID", raising=False)
    with pytest.raises(threads_api.ThreadsAPIError):
        threads_api.get_credentials()
