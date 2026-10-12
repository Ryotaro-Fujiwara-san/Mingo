import json

from fastapi.testclient import TestClient

import main


def test_users_cannot_see_or_delete_each_others_memos(tmp_path, monkeypatch):
    db_path = tmp_path / "test-memo.db"
    monkeypatch.setenv("MEMO_DB_PATH", str(db_path))

    monkeypatch.setattr(
        main,
        "split_memo",
        lambda text: {"items": [{"type": "word", "text": text}]},
    )
    monkeypatch.setattr(
        main,
        "embed_texts",
        lambda texts: [json.dumps([1.0, 0.0]) for _ in texts],
    )

    active_user = {"sub": "user-a"}

    def fake_get_current_user():
        return active_user

    monkeypatch.setitem(
        main.app.dependency_overrides,
        main.get_current_user,
        fake_get_current_user,
    )

    with TestClient(main.app) as client:
        response = client.post("/memo", json={"text": "memo-a"})
        assert response.status_code == 200

        active_user["sub"] = "user-b"
        response = client.post("/memo", json={"text": "memo-b"})
        assert response.status_code == 200

        active_user["sub"] = "user-a"
        response = client.get("/dashboard")
        assert response.status_code == 200
        a_learning = response.json()["learning"]
        assert [item["text"] for item in a_learning] == ["memo-a"]
        print("Aのダッシュボード:", response.json()["learning"])
        a_memo_id = a_learning[0]["id"]

        active_user["sub"] = "user-b"
        response = client.request("DELETE", "/delete", json={"id": a_memo_id})
        assert response.status_code == 200

        active_user["sub"] = "user-a"
        response = client.get("/dashboard")
        print("Bの削除試行後のAのダッシュボード:", response.json()["learning"])
        assert response.status_code == 200
        assert [item["text"] for item in response.json()["learning"]] == ["memo-a"]
