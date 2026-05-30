#サーバー(app)の/healthに行ったら、ちゃんとresponseが返ってくるか確かめる

from fastapi.testclient import TestClient#FastAPIから TestClientを取り出す
from main import app#main.pyの中のappを連れてくる。これをテストする
client = TestClient(app)#このサーバーに対して、本物のサーバーを起動しなくてもコードの中だけでappに話しかける

def test_health():#テストの宣言する
    response = client.get("/health")#/healthをgetする
    assert response.status_code == 200#assertでTrueかどう返答する。200なら成功
    assert response.json() == {"status":"ok"}#responseの中身をjsonでPythonが扱える形にする。
def test_cores_allows_frontend():
    response = client.get("/health",headers={"Origin":"http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
def test_websocket_echo():
    with client.websocket_connect("/ws")as ws:#使い終わったらテスト用の電話を切る
        ws.send_text("こんにちは")
        data = ws.receive_text()
        assert data == "サーバーが受け取りました:こんにちは"#ちゃんと言葉がつなっがているか確認