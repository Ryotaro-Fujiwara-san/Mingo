import asyncio
import io
import json
from types import SimpleNamespace

import pytest

import main


def test_download_colab_notebook_fetches_the_shared_file_id(monkeypatch):
    payload = {"cells": [{"cell_type": "code", "source": ["print(1)"]}]}

    def fake_urlopen(url, timeout):
        assert url == "https://drive.google.com/uc?export=download&id=FILE_ID"
        assert timeout == 20
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(main, "urlopen", fake_urlopen)

    notebook = main.download_colab_notebook(
        "https://colab.research.google.com/drive/FILE_ID#scrollTo=cell"
    )

    assert notebook == payload


def test_download_colab_notebook_rejects_non_colab_urls():
    with pytest.raises(ValueError, match="Colab"):
        main.download_colab_notebook("https://example.com/drive/FILE_ID")


def test_analyze_code_can_return_a_suggestion_without_a_notebook(monkeypatch):
    captured = {}

    class FakeMessages:
        async def create(self, **kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="text",
                        text='{"status":"ok","summary":"追加します。","suggested_code":"print(1)"}',
                    )
                ],
                stop_reason="end_turn",
            )

    class FakeClaude:
        messages = FakeMessages()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    monkeypatch.setattr(main, "AsyncAnthropic", FakeClaude)
    monkeypatch.setattr(
        main,
        "download_colab_notebook",
        lambda _: pytest.fail("No notebook URL should skip notebook download"),
    )

    result = asyncio.run(main.analyze_code("", "Add code to print 1"))

    assert result["suggested_code"] == "print(1)"
    assert result["code"] == ""
    assert "Add code to print 1" in captured["prompt"]


@pytest.mark.parametrize("needs_claude", [True, False])
def test_classify_code_request_returns_model_decision(monkeypatch, needs_claude):
    class FakeModels:
        async def generate_content(self, **kwargs):
            return SimpleNamespace(
                text=json.dumps({"needs_claude": needs_claude})
            )

    fake_client = SimpleNamespace(
        aio=SimpleNamespace(models=FakeModels())
    )
    monkeypatch.setattr(main, "client", fake_client)

    result = asyncio.run(
        main.classify_code_request("Tell me about the design choices here")
    )

    assert result is needs_claude


@pytest.mark.parametrize(
    "question",
    [
        "I need you to show me some of your Python code.",
        "I need to you to represent some your represent some Python code.",
    ],
)
def test_classify_code_request_routes_explicit_code_requests_without_gemini(
    monkeypatch, question
):
    class FakeModels:
        async def generate_content(self, **kwargs):
            pytest.fail("Explicit code requests should not need model classification")

    fake_client = SimpleNamespace(
        aio=SimpleNamespace(models=FakeModels())
    )
    monkeypatch.setattr(main, "client", fake_client)

    assert asyncio.run(main.classify_code_request(question)) is True