from types import SimpleNamespace

import main


def test_grammar_search_uses_latest_gemini_model(monkeypatch):
    call = {}

    def generate_content(**kwargs):
        call.update(kwargs)
        return SimpleNamespace(text='{"translated":"hello"}')

    monkeypatch.setattr(
        main,
        "client",
        SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)),
    )

    assert main.analyze_grammar("こんにちは", "English", "日本語") == {
        "translated": "hello"
    }
    assert call["model"] == "gemini-4-argon"
    assert call["config"].response_mime_type == "application/json"


def test_pronunciation_uses_latest_openai_tts_model(monkeypatch):
    call = {}

    def create(**kwargs):
        call.update(kwargs)
        return SimpleNamespace(content=b"audio")

    monkeypatch.setattr(
        main,
        "openai_client",
        SimpleNamespace(audio=SimpleNamespace(speech=SimpleNamespace(create=create))),
    )

    response = main.pronounce(main.PronounceIn(text="Hello", speed=0.8), user={})

    assert response.body == b"audio"
    assert call == {
        "model": "gpt-4o-mini-tts",
        "voice": "alloy",
        "input": "Hello",
        "speed": 0.8,
    }
