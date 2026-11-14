import io
import json

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