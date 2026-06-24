import httpx
import pytest

from app import llm as llm_module
from app.llm import LlmError, generate_text


def test_generate_text_returns_stripped_response(monkeypatch):
    monkeypatch.setattr(
        llm_module.httpx,
        "post",
        lambda *a, **k: httpx.Response(200, json={"response": "  hello world  \n"}),
    )
    assert generate_text("some prompt") == "hello world"


def test_generate_text_raises_llm_error_on_bad_status(monkeypatch):
    monkeypatch.setattr(llm_module.httpx, "post", lambda *a, **k: httpx.Response(500, text="oops"))
    with pytest.raises(LlmError):
        generate_text("some prompt")


def test_generate_text_raises_llm_error_on_network_failure(monkeypatch):
    def raise_request_error(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(llm_module.httpx, "post", raise_request_error)
    with pytest.raises(LlmError):
        generate_text("some prompt")
