# measure_gemini.py — Gemini Live API で FLEURS音声を文字起こしし WER を測る（フェーズ3）
import truststore
truststore.inject_into_ssl()   # SSL証明書エラーを防ぐ（このPCで必須）

import os
import sys
import asyncio

sys.stdout.reconfigure(encoding="utf-8")   # print の文字化け(cp932)エラーを防ぐ

import common
from dotenv import load_dotenv
from google import genai
from google.genai import types

# APIキーを backend/.env から読む
load_dotenv(r"C:\Users\USER\OneDrive\mingo\backend\.env")
API_KEY = os.environ.get("GEMINI_API_KEY") 

client = genai.Client(api_key=API_KEY)
MODEL = "gemini-3.1-flash-live-preview"   # 文字起こし用（半カスケード型）。translateモデルは翻訳するので不可

# 設定：応答は音声・入力音声の文字起こしを有効化・手動VAD（発話区切りを自分で指定）
CONFIG = {
    "response_modalities": ["AUDIO"],
    "input_audio_transcription": {},
    "realtime_input_config": {"automatic_activity_detection": {"disabled": True}},
}


# 音声(生PCM16バイト)をGeminiに送って、文字起こしを返す
async def transcribe(pcm_bytes):
    async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
        # (1) 「発話ここから」→ 音声を1秒ずつ送る →「発話ここまで」
        await session.send_realtime_input(activity_start=types.ActivityStart())
        chunk = 16000 * 2   # 1秒分（16000サンプル × 2バイト）
        for i in range(0, len(pcm_bytes), chunk):
            await session.send_realtime_input(
                audio=types.Blob(data=pcm_bytes[i:i + chunk], mime_type="audio/pcm;rate=16000")
            )
        await session.send_realtime_input(activity_end=types.ActivityEnd())
        # (2) 入力文字起こしを溜め、AIが喋り始めたら（＝文字起こし完成）返す
        text = ""
        async for msg in session.receive():
            sc = msg.server_content
            if sc is None:
                continue
            if sc.input_transcription and sc.input_transcription.text:
                text += sc.input_transcription.text
            if sc.model_turn is not None or sc.turn_complete:
                return text
        return text


async def main():
    clips = common.load_fleurs_clips("en_us", 50)          # 英語10件
    refs, hyps = [], []
    for audio, sr, ref in clips:
        pcm = common.audio_to_pcm16_bytes(audio, sr, 16000)  # Geminiは16kHz（変換なし）
        hyp = await transcribe(pcm)
        refs.append(ref)   # 正解を貯める
        hyps.append(hyp)   # 出力を貯める
    print("WER:", common.score(refs, hyps))


asyncio.run(main())
