import truststore
truststore.inject_into_ssl()

import re #正規表現
import base64#音声をbase64にする
import numpy as np#配列の計算をする。
import librosa#16kHzを24kHzに変換する
import jiwer#WER計算をする
from datasets import load_dataset#FLEURS読み込みをする
import csv #csv保存用

#==FLEURSからn件だけ音声を取得する関数 ==#
def load_fleurs_clips(lang,n,split="test"):
    ds = load_dataset("google/fleurs",lang,split=split,streaming=True)#streaming=Trueで一件ずつダウンロードする
    clips = []
    for s in ds:
        clips.append((s["audio"]["array"],s["audio"]["sampling_rate"],s["transcription"]))#波形、レート（16000）、正解文
        if len(clips) >= n:#n件より多ければループを停止
            break
    return clips


#==音声変換をする関数（生バイト版：Gemini用） ==#
def audio_to_pcm16_bytes(audio,from_rate,to_rate):#audio=波形,from_rate=元のレート（16000）,to_rate=目標レート（OpenAIは24000,Geminiは16000)
    if from_rate != to_rate:#OpenAIの時だけ変換（Geminiは16000のまま＝ここを飛ばす）
        audio = librosa.resample(audio,orig_sr=from_rate,target_sr=to_rate)#16000を24000にする
    pcm16 = (np.clip(audio,-1,1)*32767).astype(np.int16)#PCM(-32767から32767)に小数(-1.0から1.0)を変換する。.astype(np.int16)でそれを整数(16bit)に変換する（PCM16）
    return pcm16.tobytes()#生のバイト列を返す（Geminiはこのまま送る）

#==音声変換をする関数（base64版：OpenAI用） ==#
def audio_to_pcm16_base64(audio,from_rate,to_rate):#上の生バイトをbase64文字にするだけ
    return base64.b64encode(audio_to_pcm16_bytes(audio,from_rate,to_rate)).decode()#OpenAIはJSONで送るのでbase64文字が必要

#==正規化をする関数 ==#
def normalize(text):
    text = text.lower()#小文字化
    text = re.sub(r"[^\w\s]","",text)#句読点を除去
    text = re.sub(r"\s+"," ",text).strip()#連続空白を一つにして、前後の空白を除去する
    return text

#==WER計算をする関数 ==#
def score(refs,hyps):
    refs = [normalize(r) for r in refs]#正解を全部正規化
    hyps = [normalize(h) for h in hyps]#出力を全部正規化
    return jiwer.wer(refs,hyps)


