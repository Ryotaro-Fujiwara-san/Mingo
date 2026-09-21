# measure_openai.py — OpenAI Realtime で FLEURS音声を文字起こしし WER を測る（フェーズ1：1クリップ）
import os
import sys
import json
import asyncio

sys.stdout.reconfigure(encoding="utf-8")   # print の文字化け(cp932)エラーを防ぐ

import common                      
import websockets
from dotenv import load_dotenv

# APIキーを backend/.env から読む
load_dotenv(r"C:\Users\USER\OneDrive\mingo\backend\.env")
API_KEY = os.environ["OPENAI_API_KEY"]

REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime"


# 音声(base64)をOpenAIに送って、文字起こしを返す
async def transcribe(b64_audio):
    headers = [("Authorization", "Bearer " + API_KEY)]
    async with websockets.connect(REALTIME_URL, additional_headers=headers, max_size=16 * 1024 * 1024) as ws:
        # (1) 設定：文字起こし有効・手動確定（turn_detection=None）
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "type": "realtime",
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "turn_detection": None,
                        "transcription": {"model": "gpt-4o-transcribe"},
                    }
                },
            },
        }))
        # (2) 音声を送る → 確定
        await ws.send(json.dumps({"type": "input_audio_buffer.append", "audio": b64_audio}))#音声をバッファに追加（音声を送る）
        await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))#commitで音声処理を確定する（音声送信を終わり処理する）
        # (3) 文字起こしを待って返す
        async for msg in ws:
            m = json.loads(msg)#届いた文字列をオブジェクトに変換
            if m["type"] == "conversation.item.input_audio_transcription.completed":#文字起こし完了イベントが来たら、その文字を返す
                return m["transcript"]
            if m["type"] == "error":#エラーなら諦めて
                return ""


async def main():
    clips = common.load_fleurs_clips("en_us", 50)          # 英語1件
    audio, sr, refs,hyps = [],[],[],[]
    for audio,sr,ref in clips:
        b64 = common.audio_to_pcm16_base64(audio, sr, 24000)  # OpenAIは24kHz
        hyp = await transcribe(b64)
        refs.append(ref)#正解を貯める
        hyps.append(hyp)#出力を貯める
    print("WER:", common.score(refs, hyps))


asyncio.run(main())
