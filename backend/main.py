import os#.envのキーをos.environから取る
import asyncio#並列処理をする
import json
import truststore
truststore.inject_into_ssl()

import websockets
from dotenv import load_dotenv

from pydantic import BaseModel #型チェックの土台を取り出す。これがあるおかげで自動でJSONがチェックされる。
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

##== フロントから届くJSONの「型」を定義 ==##
class SessionConfig(BaseModel):
    role:str#AIの属性（文字）
    situation:str#シチュエーション（文字）
    targetLang:str#学習言語（文字）
    explainLang:str#母国語（文字）
    speed:float#会話速度（小数）


##== APIにわかるようにJSONからの返答の形式を整える ==##
def build_instructions(config:SessionConfig):
    return(
        f"You are {config.role}.The situation is:{config.situation}."
        f"When you answer use {config.explainLang}."
        f"Keep your replies 7 sentences."
    )

##== エンドポイントを作成する ==##
app = FastAPI()#サーバー本体
load_dotenv()#.envからAPIキーを読む

REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime"  # OpenAIの音声窓口の住所


@app.websocket("/realtime")        # フロントで「確定」ボタンを押すとURLが起動しこのエンドポイントが起動する
async def realtime(websocket:WebSocket): #エンドポイントが起動後にこの関数のみ自動で処理される
    await websocket.accept()
    first = await websocket.receive_text()
    config = SessionConfig(**json.loads(first))
    instructions = build_instructions(config)
    api_key = os.environ.get("OPENAI_API_KEY")
    headers = [("Authorization","Bearer "+api_key )]
    async with websockets.connect(
        REALTIME_URL,
        additional_headers=headers,
        max_size=16*1024*1024,
    )as openai_ws:

        await openai_ws.send(json.dumps({
            "type":"session.update",#メッセージの種類を「設定の更新」にする
            "session":{#設定の中身
                "type":"realtime",
                "output_modalities":["audio"],#返事を音声にする
                "instructions":instructions,#build_instructions(config)で作ったAIに対する指示文
                "audio":{
                    "input":{
                        "format":{"type":"audio/pcm","rate":24000},
                        "turn_detection":{
                            "type":"semantic_vad",
                            "eagerness":"low",
                        },#意味的に話し終わったかで区切る（eagerness:low=しっかり待つ）
                        "transcription":{"model":"gpt-4o-transcribe"},
                    },#マイク側の設定
                    "output":{
                        "format":{"type":"audio/pcm","rate":24000},
                        "voice": "marin",
                    }#スピーカー側の設定（速度はクライアント側で調整）
                },
            },
        }))

       
        async def frontend_to_openai():
            try:
                while True:
                    msg = await websocket.receive_text()
                    await openai_ws.send(msg)
            except WebSocketDisconnect:
                pass

        async def openai_to_frontend():
            try:
                async for msg in openai_ws:
                    await websocket.send_text(msg)
            except websockets.exceptions.ConnectionClosed:
                pass

        task_a = asyncio.create_task(frontend_to_openai())
        task_b = asyncio.create_task(openai_to_frontend())
        await asyncio.wait({task_a, task_b}, return_when=asyncio.FIRST_COMPLETED)
        task_a.cancel()
        task_b.cancel()
