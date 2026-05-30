import os
import asyncio  # 複数のことを同時にやるための道具
import json
import truststore
truststore.inject_into_ssl()  # ブラウザ(Windows)が信頼する証明書をPythonにも使わせる(SSL検査対策)

import httpx
import websockets  # バックエンドがOpenAIのWebSocketにお客さんとしてつなぐための道具
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()  # .env を読み込んでキーを環境変数に入れる

app = FastAPI()

app.add_middleware(  # あるアドレス(localhost:5173)が別アドレス(127.0.0.1:8000)を勝手に呼ぶのを、許可が無ければブラウザがブロックする。その許可を出す門番
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")  # /health に GET が来たら下の関数を呼ぶ
def health():
    return {"status": "ok"}


class AskRequest(BaseModel):  # /ask に来るデータは message という文字が入ったJSON、という設計図
    message: str


@app.post("/ask")  # /ask への POST を受ける宣言
async def ask(req: AskRequest):  # 届いたデータが AskRequest の形で req に入る
    api_key = os.environ.get("OPENAI_API_KEY")  # .env から読んだキーを取り出す
    async with httpx.AsyncClient() as client:  # 通信の道具を開いて使って、自動で閉じる
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",  # 送る宛先(URL)
            headers={"Authorization": f"Bearer {api_key}"},  # キーを添えて身分証明(Bearerの後ろは半角スペース)
            json={
                "model": "gpt-4o-mini",  # 使うAI(まずは安いモデルで動作確認)
                "messages": [{"role": "user", "content": req.message}],  # userの発言=フロントから来た質問
            },
            timeout=30,  # 30秒返事が来なければ諦める
        )
    data = response.json()  # 返ってきたJSONを取り出す
    answer = data["choices"][0]["message"]["content"]  # JSONの奥からAIの答えの文字を取り出す
    return {"answer": answer}  # フロントに答えを返す


# ===== リアルタイム音声会話 =====
REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime"  # OpenAIリアルタイム窓口の住所
SESSION_CONFIG = {  # つないだ直後に送る設定書
    "type": "session.update",
    "session": {
        "type": "realtime",
        "output_modalities": ["audio"],
        "instructions": "あなたは親しみやすい会話相手です。返事は１文",
        "audio": {
            "input": {
                "format": {"type": "audio/pcm", "rate": 24000},
                "turn_detection": {"type": "server_vad"},
            },
            "output": {
                "format": {"type": "audio/pcm", "rate": 24000},
                "voice": "marin",
            },
        },
    },
}


@app.websocket("/realtime")  # /realtime にWebSocket接続が来たら下の関数を呼ぶ
async def realtime(websocket: WebSocket):
    await websocket.accept()  # ブラウザの電話を受ける
    api_key = os.environ.get("OPENAI_API_KEY")
    headers = [("Authorization", "Bearer " + api_key)]  # OpenAIに見せる身分証
    async with websockets.connect(REALTIME_URL, additional_headers=headers, max_size=16 * 1024 * 1024) as openai_ws:  # OpenAIに電話をかける
        await openai_ws.send(json.dumps(SESSION_CONFIG))  # つないだ直後に設定書を送る

        async def frontend_to_openai():  # ブラウザ → OpenAI へ運ぶ係
            try:
                while True:
                    msg = await websocket.receive_text()  # ブラウザから受け取る
                    await openai_ws.send(msg)  # OpenAIへ流す
            except WebSocketDisconnect:  # ブラウザが切ったら
                pass

        async def openai_to_frontend():  # OpenAI → ブラウザ へ運ぶ係
            async for msg in openai_ws:  # OpenAIから届くたびに
                await websocket.send_text(msg)  # ブラウザへ流す

        ft = asyncio.create_task(frontend_to_openai())  # 2つの係を同時に走らせる
        ot = asyncio.create_task(openai_to_frontend())
        done, pending = await asyncio.wait({ft, ot}, return_when=asyncio.FIRST_COMPLETED)  # どちらか終わるまで待つ
        for task in pending:  # 残った係を止めて後片付け
            task.cancel()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):  # websocketという名前でWebSocket回線を1つ受け取る
    await websocket.accept()  # かかってきた電話を受ける
    try:
        while True:  # つなぎっぱなしでずっと聞き続ける
            data = await websocket.receive_text()  # 相手の言葉を待って受け取る
            await websocket.send_text("サーバーが受け取りました:" + data)  # 頭に文を付けて返す(やまびこ)
    except WebSocketDisconnect:  # 相手がタブを閉じたとき
        pass  # エラーで落ちないようにする
