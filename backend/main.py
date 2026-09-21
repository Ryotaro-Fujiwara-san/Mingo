import os#.envのキーをos.environから取る
import asyncio#並列処理をする
import time#ID用のタイマ
import json
import wave
import azure.cognitiveservices.speech as speechsdk#Azureの音声機能をspeechsdkと名前つけた
import tempfile
import base64#フロントのbase64音声を生バイトに戻す
import truststore
import sqlite3#SQLiteのライブラリ
import math#平方根などの計算用
from watchdog.events import FileSystemEventHandler#ファイルの変化を自動認識するライブラリ
truststore.inject_into_ssl()
from watchdog.observers import Observer

from dotenv import load_dotenv

from pydantic import BaseModel #型チェックの土台を取り出す。これがあるおかげで自動でJSONがチェックされる。
from fastapi import FastAPI, WebSocket, WebSocketDisconnect,Response
from fastapi.middleware.cors import CORSMiddleware#CORSの許可を取る 
from google import genai#Geminiと話すSDK
from openai import OpenAI#OpenAIと話すSDK
from google.genai import types #Blobなどの型
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage#Claudeに対する操作






##== メモ・ヒント機能用のテーブルを作る関数を定義 ==##
def init_memo_db():
    conn = sqlite3.connect("memo.db")
    ##== メモ・ヒント機能用のDBを定義 ==##
    conn.execute("""CREATE TABLE IF NOT EXISTS memo_item(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        text TEXT NOT NULL,
        vector TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        last_seen_at TEXT,
        half_life REAL DEFAULT 1.0,
        good INTEGER DEFAULT 0,
        bad INTEGER	DEFAULT 0,
        hint_free_success INTEGER DEFAULT 0
    )""")
    ##== ダッシュボード用のDBを定義 ==##
    conn.execute("""CREATE TABLE IF NOT EXISTS mastered(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        mastered_at TEXT DEFAULT (datetime('now'))
    )""")

    conn.commit()#変更を確定し、テーブルを作成
    conn.close()#DBへの接続を閉じる
init_memo_db()#起動時にメモ・ヒント用のDBを起動（memo_itemとmasteredの両方を作る）


##== 発音検索でフロントから届くJSONの「型」を定義 ==##
class PronounceIn(BaseModel):
    text:str#読み上げる文章
    speed:float#読み上げる速度

##== メモ・ヒントでフロントからユーザーの発言とヒントの「型」を定義 ==##
class Interaction(BaseModel):
    utterance:str#ユーザーの発言
    shown:list[str]#ヒントで見せた表現のリスト

##== 削除するメモのIDの「型」を定義 ==##
class DeleteIn(BaseModel):
    id:int#消すメモのid

##== ヒント検索で受け取るデータの「型」を定義 ==##
class HintIn(BaseModel):
    query:str#AIの直前の発言

##== フロントから届くメモのJSONの「型」を定義 ==##
class MemoIn(BaseModel):
    text:str#表現そのもの

##== 文法検索でフロントから届くJSONの「型」を定義 ==##
class GrammarSearchIn(BaseModel):
    text:str#解析したい文章（フェーズ3では「タップした節」もここに入る）
    targetLang:str#学習言語
    explainLang:str#母国語（意味・解説をこの言語で書く）
    context:str = ""#その節が入っていた元の文、もし無ければ空文とする

##== フロントから届くAIの設定のJSONの「型」を定義 ==##
class SessionConfig(BaseModel):
    role:str#AIの属性（文字）
    situation:str#シチュエーション（文字）
    targetLang:str#学習言語（文字）
    explainLang:str#母国語（文字）
    speed:float#会話速度（小数）
    watchPath:str = ""#監視フォルダのパス（空でもOK）


##== APIにわかるようにJSONからの返答の形式を整える ==##
def build_instructions(config:SessionConfig):
    return(
        f"You are {config.role}.The situation is:{config.situation}."
        f"When you answer use {config.targetLang}."
        f"Keep your replies 7 sentences."
        f"IMPORTANT: If the user asks you to check, read, explain, review, or fix any file or code, you MUST call the analyze_code tool. Never say you cannot access files. This rule overrides your persona and situation."
    )

##== エンドポイントを作成する ==##
app = FastAPI()#サーバー本体
load_dotenv()#.envからAPIキーを読む
API_KEY = os.environ.get("GEMINI_API_KEY")#.envからGeminiのキーを取り出す
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")#.envからOpenAIのキーを取り出す
AZURE_KEY = os.environ.get("AZURE_SPEECH_KEY")#.envからAzureのキーを取り出す
AZURE_REGION = os.environ.get("AZURE_SPEECH_REGION")#.envからAZURE_SPEECH_REGIONのキーを取り出す
openai_client = OpenAI(api_key = OPENAI_API_KEY)#openaiライブラリの中にある設計図Clientを使って、APIキー付きで“実物の道具箱”を1個作り、それをopenai_clientという変数に入れる
client = genai.Client(api_key = API_KEY)#genaiライブラリの中にある設計図Clientを使って、APIキー付きで“実物の道具箱”を1個作り、それをclientという変数に入れる
MODEL = "gemini-3.1-flash-live-preview"
GRAMMER_MODEL = "gemini-3.5-flash-lite"
PRON_MODEL = "gemini-3.5-flash-lite"

##== CORSでバックエンドで送信を許可する==##
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],#どこからのアクセスも許可
    allow_methods = ["*"],
    allow_headers = ["*"],
)


##== ファイル監視　==##
current = {"path":None}#今のファイルの中身を共有する
observer_holder = {"observer":None}#今動いているファイルがどれかを監視する


##== ファイルが変更されたらそのパスを保存するクラスを用意する　==##
class ChangeHandler(FileSystemEventHandler):
    def on_modified(self,event):
        if not event.is_directory:#ファイルの変更である場合
            current["path"] = event.src_path#現在の変更されたファイルのパスを保存する

##== ファイルの変更を監視する　==##
def start_watcher(watch_dir):#パスを引数で受け取る
    current["folder"] = watch_dir#作業フォルダを保存
    if not watch_dir:#パスが空なら何もしない
        return
    old = observer_holder["observer"]#前のオブザーバーを保存する
    
    if old:#前のオブザーバーがあれば、それを停止する
        old.stop()
    observer = Observer()#watchdogが用意したカメラの設計図（クラス）を実体化し、後で使えるようにする。
    observer.schedule(ChangeHandler(),path=watch_dir,recursive=True)#渡されたパスを監視し、サブフォルダまでrecursive=Trueにより見張らせる。またChangeHandler()により変更が起きたらon_modifiedを実行する。
    observer.start()#監視開始
    observer_holder["observer"] = observer#今のオブザーバーを保存する


##== アドバイス関数を司令する関数 ==##
async def analyze_turn(user_text,utterance_audio,websocket,config:SessionConfig,turn_id):
    result = await check_grammar(user_text,websocket,config,turn_id)
    if result and result.get("correct") and utterance_audio:#文法OK＆音声があるとき
        try:
            weak = await asyncio.to_thread(assess_pronunciation,utterance_audio,user_text)
        except Exception as e:
            print("発音採点　エラー",e)
            weak = None
        if weak:#弱点があるとき
            await pronunciation_advice(weak,websocket,config,turn_id)
        elif weak == "":#認識OKだが弱点ゼロ→発音問題無し
            await websocket.send_text(json.dumps({
                "type":"pronunciation_feedback",
                "result":json.dumps({"advice":[]}),#空リスト＝問題なし
                "id":turn_id,
            }))
    

##== 文法アドバイス ==##
async def check_grammar(text,websocket,config:SessionConfig,turn_id):
    prompt = (
        "次の文章が文法的に正しいか判定して、必ずJSONだけで返す:\n"
        '{"correct":true/false,"corrected":"修正分","explanation":"理由の解説"}\n'
        f"explanationは{config.explainLang}で書くこと\n"
        f"文:{text}"
    )
    try:
        response = await client.aio.models.generate_content(#非同期にすることで、他の処理（特にリアルタイム会話）が止まらないようにする
            model=GRAMMER_MODEL,
            contents = prompt,
            config=types.GenerateContentConfig(
                response_mime_type = "application/json",#形式（JSON）
                temperature = 0.2,#答えのブレ具合（低いと堅実）
            )
        )
        await websocket.send_text(json.dumps({
            "type":"grammar_feedback",
            "result":response.text,#判定結果のJSON文字列
            "id":turn_id,#どの発言に対する訂正か判別する
        }))
        return json.loads(response.text)

    except Exception as e:
        return None

##== 発音アドバイス==##
async def pronunciation_advice(weak_spots,websocket,config:SessionConfig,turn_id):
    prompt = (
        "これは目標言語学習者の発音の弱点データです。各弱点について、口や舌の動かし方を初心者にもわかる具体的なアドバイスにして。必ずJSONだけで返す:\n"
        '{"advice":[{"target":"対象の単語や音","tip":"直し方"}]}\n'
        f"tipは{config.explainLang}で書くこと\n"
        f"弱点データ:{weak_spots}"
    )
    try:
        response = await client.aio.models.generate_content(#非同期にすることで、他の処理（特にリアルタイム会話）が止まらないようにする
            model=PRON_MODEL,
            contents = prompt,
            config=types.GenerateContentConfig(
                response_mime_type = "application/json",#形式（JSON）
                temperature = 0.2,#答えのブレ具合（低いと堅実）
            )
        )
        await websocket.send_text(json.dumps({
            "type":"pronunciation_feedback",
            "result":response.text,#判定結果のJSON文字列
            "id":turn_id,#どの発言に対する訂正か判別する
        }))

    except Exception as e:
        print("発音アドバイス　エラー",e)
        

##== 発音チェック(Azuraに音素レベルで採点してもらう) ==##
def assess_pronunciation(pcm,reference):
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY,region=AZURE_REGION)
    #一時ファイルを使わず、音声(pcm)を直接Azureに流す（16kHz・16bit・モノラル）
    stream_format = speechsdk.audio.AudioStreamFormat(samples_per_second=16000,bits_per_sample=16,channels=1)
    push_stream = speechsdk.audio.PushAudioInputStream(stream_format)
    push_stream.write(pcm)#音声データを流し込む
    push_stream.close()#これで終わり、と伝える
    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
    pron_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference,#お手本＝文字起こし
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,#100点単位で採点
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,#音素まで細かく
    )
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config,audio_config=audio_config)
    pron_config.apply_to(recognizer)
    result = recognizer.recognize_once()

    if result.reason != speechsdk.ResultReason.RecognizedSpeech:
        return None#認識できなかった（弱点ゼロとは区別する）
    pron = speechsdk.PronunciationAssessmentResult(result)
    weak = []#弱点をためるリスト
    for w in pron.words:
        for p in w.phonemes:
            if p.accuracy_score < 80:
                weak.append(f"{w.word}の{p.phoneme}({int(p.accuracy_score)}点)")
    return "、".join(weak)

#== メモした表現を分解する関数 ==##
def split_memo(text):
    promot = (
        "次の文章から、学習価値のある単語・イディオム・構文を抜き出して分類し、必ずJSONだけで返して:\n"
        '{"items":[{"type":"wordかidiomかsyntax","text":"抜き出した表現"}]}\n'
        f"抜き出した文章:{text}"
    )
    response = client.models.generate_content(
        model = GRAMMER_MODEL,
        contents = promot,
        config=types.GenerateContentConfig(
                response_mime_type = "application/json",#形式（JSON）
                temperature = 0.2,#答えのブレ具合（低いと堅実）
        ),
    )
    return json.loads(response.text)

#== メモした表現を意味ベクトル化する関数 ==##
def embed_texts(texts):
    response = openai_client.embeddings.create(
        model = "text-embedding-3-large",
        input = texts,
    )
    return[ json.dumps(d.embedding)for d in response.data]

#== 二つのベクトルの意味的な近さを測るコサイン類似度関数 ==##
def cosine_similarity(a,b):
    dot = sum(x*y for x,y in zip(a,b))#各要素をかけた合計の内積
    norm_a = math.sqrt(sum(x*x for x in a))#aの長さ
    norm_b = math.sqrt(sum(x*x for x in b))#bの長さ
    return dot/(norm_a * norm_b)

#== HLRの重み ==#
THETA_BIAS = 0.0    # 基準
THETA_GOOD = 1.0    # 正解回数の重み
THETA_BAD  = -1.0   # 不正解回数の重み

#== その他の定数 ==#
DELETE_MAX = 5#ヒント無しで成功できた回数の最高値
HALF_LIFE_MAX = 180#半減期の最高値

#== 今のHLRを計算する ==#
def recall_probability(good,bad,delta_days):
    if delta_days is None:#一度も使っていない（Δ=0）新規メモは最優先で出す
        return 0
    h = 2**(THETA_BIAS + THETA_GOOD*math.sqrt(good) + THETA_BAD*math.sqrt(bad))
    return 2**(-delta_days/h)#想起確率（０から１） 

#== 上位の表現を組み合わせて、今の会話で使える例文をLLMが生成する ==#
def make_example(hints,ai_text):
    exprs = ",".join(f"{h['type']}:{h['text']}" for h in hints)#表現を一行にして繋げる
    promot = (
        "外国語学習のヒントを作ります。次のAIの回答文への返答として、下の表現をできるだけ使った自然な例文を一つ作りなさい。必ずJSONだけで返してください:\n"
        '{"example":"作った例文","used":["使った表現",....]}\n'
        f"AIの発言:{ai_text}\n"
        f"使ってほしい表現:{exprs}\n"
    )
    response = client.models.generate_content(
        model= GRAMMER_MODEL,
        contents = promot,
        config = types.GenerateContentConfig(
                response_mime_type = "application/json",#形式（JSON）
                temperature = 0.2,#答えのブレ具合（低いと堅実）
        ),
    )
    return json.loads(response.text)

#== ユーザーの発言で使われた表現をLLMに判定させる ==#
def judge_used(utterance,expressions):
    promot = (
        "ユーザーの発言と、注目している表現リストがあります。発言の中で実際に使われた表現だけを返して。また活用形・言い換えも「使った」とみなす。また必ずJSONだけで返す:\n"
        '{"used":["実際に使われた表現",...]}\n'
        f"発言:{utterance}\n"
        f"表現リスト:{expressions}"
    )
    response = client.models.generate_content(
        model= GRAMMER_MODEL,
        contents = promot,
        config = types.GenerateContentConfig(
                response_mime_type = "application/json",#形式（JSON）
                temperature = 0.2,#答えのブレ具合（低いと堅実）
        ),
    )
    return json.loads(response.text).get("used",[])#実際に使われた表現


#== メモを保存する機能 ==#
@app.post("/memo")
def save_memo(item:MemoIn):
    result = split_memo(item.text)
    conn = sqlite3.connect("memo.db")

    #重複を除いた新しい要素だけを集める
    new_items = []#新しい要素を格納する変数
    seen_texts = set()#同じ値が重複しない集合を作成
    for el in result["items"]:
        text = el["text"]#表現のみ格納
        exists = conn.execute("SELECT 1 FROM memo_item WHERE text = ?",(el["text"],)).fetchone()
        if not exists and text not in seen_texts:#DBにも無く、今回の処理中にも重複して無ければ
            new_items.append(el)#表現が重複していなければ、その値を新しい要素を格納する変数に格納する
            seen_texts.add(text)#一時的に今回の処理の間だけ表現を保存
    #新しい要素のtextをまとめてベクトル化する
    if new_items:
        vectors = embed_texts([el["text"] for el in new_items])
        for el,vector in zip(new_items,vectors):
            conn.execute("INSERT INTO memo_item(type,text,vector) VALUES(?,?,?)",(el["type"],el["text"],vector,))
    conn.commit()
    conn.close()
    return{"status":"SAVED"}#フロントにJSONで返答する

#== ヒントを提示する機能 ==#
@app.post("/hint")
def get_hint(item:HintIn):
    q_vec = json.loads(embed_texts([item.query])[0])#queryの一件目[0]をベクトル化し、それをPytonのリストに戻す
    conn = sqlite3.connect("memo.db")
    rows = conn.execute("SELECT type,text,vector,good,bad,julianday('now')-julianday(last_seen_at) AS delta_days FROM memo_item").fetchall()#全メモから拾い
    conn.close()
    scored=[]
    for type_,text_,vector_,good_,bad_,delta_days_ in rows:#書くメモと類似度を計算
        if not vector_:#vectorが空（古いメモ）は飛ばす
            continue
        v = json.loads(vector_)
        sim = cosine_similarity(q_vec,v)
        p = recall_probability(good_,bad_,delta_days_)
        scored.append((sim,p,type_,text_))
    scored.sort(key=lambda s:s[0], reverse=True)#類似度s[0]が高い順に並べる。（reverse=Trueで適用する）特にsimが高い順に並べる
    relevant = scored[:5]#上位5件
    relevant.sort(key=lambda s:s[1])#さらにその中で想起確率s[1]が低い順
    top = relevant[:4]#さらにその中の上位５件
    hints = [{"type":t,"text":tx} for sim,p,t,tx in top]
    example = make_example(hints,item.query)
    return {"hints":hints,"example":example.get("example","")}

#== ヒントの使用状況を判定して習得度を更新する機能 ==#
@app.post("/interaction")
def record_interaction(item:Interaction):
    conn = sqlite3.connect("memo.db")
    rows = conn.execute("SELECT id,text,good,bad,hint_free_success FROM memo_item").fetchall()#全メモを取り出す
    all_texts = [r[1] for r in rows]#textのみ取り出す
    used = judge_used(item.utterance,all_texts)#実際に使われた表現
    for id_,text_,good_,bad_,hint_free_success_ in rows:
        is_used = text_ in used#実際に使われたか
        is_shown = text_ in item.shown#ヒントで見せたか
        if is_used and is_shown:#①ヒントを使った成功
            conn.execute("UPDATE memo_item SET good=good+1, last_seen_at=datetime('now') WHERE id=?",(id_,))
        elif is_used and not is_shown:#③ヒント無しで成功
            conn.execute("UPDATE memo_item SET good=good+2, hint_free_success=hint_free_success+1, last_seen_at=datetime('now') WHERE id=?",(id_,))
            if hint_free_success_ + 1 >= DELETE_MAX and recall_probability(good_+2, bad_, HALF_LIFE_MAX) >= 0.5:#習得済み
                conn.execute("DELETE FROM memo_item WHERE id=?",(id_,))
        elif is_shown and not is_used:#②失敗（見たのに使わなかった）
            conn.execute("UPDATE memo_item SET bad=bad+1 WHERE id=?",(id_,))
    conn.commit()
    conn.close()
    return {"status":"updated","used":used}

#== 進捗ダッシュボードに必要な情報を取得する機能 ==#
@app.get("/dashboard")
def dashboard():
    conn = sqlite3.connect("memo.db")
    rows = conn.execute("SELECT id,type,text,hint_free_success FROM memo_item").fetchall()
    mastered_count = conn.execute("SELECT COUNT(*) FROM mastered").fetchone()[0]#masterdから習得した表現（行）の数を習得し、(?.)タプルから[0]で?のみ取得する
    conn.close()
    learning = [{"id":id_,"type":type_,"text":text_,"hint_free_success":hfs_} for id_,type_,text_,hfs_ in rows]#rows = [(1,"word","juicy",2), (2,"idiom","get rid of",0)]から{"id":1,"type":"word","text":"juicy","hint_free_success":2},{"id":2,"type":"idiom","text":"get rid of","hint_free_success":0}のように(id, type, text, hint_free_success)の各行をid_, type_, text_, hfs_の4つの変数に分けて取り出し、{"id":id_, "type":type_, "text":text_, "hint_free_success":hfs_}という辞書を作る
    return{"mastered_count":mastered_count,"learning":learning}

#== メモの表現を削除する機能 ==#
@app.delete("/delete")
def delete_memo(item:DeleteIn):
    conn = sqlite3.connect("memo.db")
    conn.execute("DELETE FROM memo_item WHERE id=?",(item.id,))
    conn.commit()
    conn.close()
    return{"status":"deleted"}

    
##== コード分析ツールを定義する ==##
CODE_TOOL = types.Tool(
    function_declarations=[#ライブラリがリストにしろと決めているため、リストの形式にする
        types.FunctionDeclaration(
            name = "analyze_code",#実行したい関数
            description ="ユーザーが今作業中のファイル（コード・README・設定ファイル等）の確認・説明・修正・要約を頼んだら必ず呼ぶ。ファイルの中身は自分で読めるので『アクセスできない』とは言わず必ずこのツールを使う。",
            parameters = types.Schema(#関数データがどんな形かを表す設計図を書く
                type = types.Type.OBJECT,#これは固定された書き方であり、OBJECT形式(辞書）で渡すようにする
                properties = {
                    "request":types.Schema(#さらにその関数の引数のデータがどんな形かを表す設計図を各
                        type = types.Type.STRING,#STRING形式（文字）で渡すようにする
                        description = "ユーザーがしてほしいこと"
                    ),
                },
            ),#実行したい関数の引数の様式を決定する
        )
    ]
)

##== コード分析をClaudeに依頼する関数 ==##
async def analyze_code(request,lang):
    path = current["path"]
    if path:
        folder = os.path.dirname(path)#os.path.dirname()は「ファイルのパスから、入っているフォルダを取り出す」定型文
    else:
        folder = current.get("folder")#無ければ入力した作業フォルダ
    if not folder:#どちらも無ければ終了
        return{"summary":"作業フォルダがありません。","code":""}

    prompt = (
            f"ファイル{path}について次の依頼に答えて:{request}\n"
            f"コード内のコメントは必ず{lang}で書くこと\n"
            f"必ず次のJSON形式だけで答えること（前後に他の文字を書かない）:\n"
            f'{{"summary":"音声で話すための短い要約。コードは絶対に入れない","code":"コードや具体的な変更点。無ければ空文字"}}'
    )
    options = ClaudeAgentOptions(
            cwd = folder,#Claudeが探索するフォルダ
            allowed_tools = ["Read","Grep","Glob"],#読むことだけ許可する
            permission_mode="bypassPermissions",#毎回確認は出さない
            max_turns = 10,#思考往復の上限
    )

    try:
        text = ""
        async for message in query(prompt = prompt,options = options):#プロンプトとオプションを送信し、返答を一個ずつmessageへ取り出す
            if isinstance(message,ResultMessage):#取り出した内容の種類が、Claudeが返答した思考軌跡ではなく最終結論なら
                text = message.result#最終結果をtextに格納
        start = text.find("{")#JSONの始まり
        end = text.rfind("}")#JSONの終わり
        data = json.loads(text[start:end+1])#{}部分のみJSONに変換
        return {"summary":data.get("summary",""),"code":data.get("code","")}#返答が無ければ""を返答する
    except Exception as e :
        import traceback; traceback.print_exc()#全トレースバックをターミナルに出す
        cause = getattr(e, "__cause__", None)#SDKが包む前の“本当の例外”
        return{"summary":f"分析エラー:{type(e).__name__}|原因:{type(cause).__name__}:{cause}","code":""}

#== 入力文を解析して役割・文法・意味を返す関数 ==#
def analyze_grammar(text,target_lang,explain_lang,context=""):
    context_line = ""
    if context:
        context_line = (
            f"参考(元の文):{context}\n"
            "↑これは解析対象が入っていた元の文。関係代名詞・指示語が指す先行詞は"
            "この元の文から判断してmeaningに反映する(例:who→『the boy(その少年)を指す』)。"
            "ただし分割・解析するのは『解析対象』だけで、元の文は分割しない。\n"   
        )
    prompt=(
         f"あなたは語学教師です。学習言語={target_lang}、母国語={explain_lang}。\n"
        "次の手順で解析対象を解析し、JSONだけで返す。\n"
        "手順1:解析対象が母国語なら学習言語に翻訳、すでに学習言語ならそのまま使う(結果をtranslated、翻訳したかをwasTranslatedに)。\n"
        "手順2:(翻訳後の)全文の意味を母国語でall_meaningに入れる。\n"
        "手順3:ピリオドなどで文単位(sentences)に分け、各文の意味を母国語でsub_meaningに入れる。\n"
        "手順4:各文を『読む順のまま・一番外側の層だけ』でsegmentsに区切る。関係詞節・従属節・to不定詞句などの『さらに分解できるまとまり』はそれ以上分解せずrole=\"clause\"の1要素にまとめる(中は展開しない)。【最重要】解析対象そのものの全体を1つのsegment(特にrole=clause)にしてはいけない。解析対象は必ず内部を2つ以上のsegmentに分解する。role=\"clause\"にできるのは『解析対象の“内部”にある、より小さい節・句』だけで、解析対象と同じ範囲をclauseにしてはいけない。\n"
        "手順5:各segmentにrole(S/V/O/C/idiom/clause/other)、meaning(意味の解説)、caseInflection(格変化・活用の解説。無ければ空)を付ける。role=clauseの時だけclauseType(節の種類)も付ける。制限用法だけでなく非制限用法(例:「, which is really handsome」「, who ...」のようにカンマで始まる節)も、カンマごとrole=\"clause\"にする。分詞句は現在分詞(例:「playing football」)・過去分詞(例:「written in English」)のように名詞を修飾する句も含める。慣用句・イディオム・句動詞(例:「by the way」「look forward to」「give up」「as soon as possible」)は、バラバラの語に分けず、まとめて1つのrole=\"idiom\"にする。\n"
        "textは入力の語をそのまま写す。meaning・caseInflection・all_meaning・sub_meaningは必ず母国語で書く。\n"
        "必ず次のJSON形式だけで返す:\n"
        '{"wasTranslated":true/false,"translated":"学習言語での全文","all_meaning":"全文の母国語での意味",'
        '"sentences":[{"text":"文","sub_meaning":"その文の母国語での意味",'
        '"segments":[{"text":"語や句","role":"S/V/O/C/idiom/clause/other",'
        '"meaning":"母国語での意味の解説","caseInflection":"格変化・活用の解説。特に原形となぜその格変化をしたのか初学者にわかるように丁寧に。特に格変化の際にどのように語尾が変化するについても(母国語)",'
        '"clauseType":"role=clauseの時だけ節の種類"}]}]}\n'
        + context_line +
        f"解析対象:{text}"    
    )
    response = client.models.generate_content(
        model = GRAMMER_MODEL,
        contents = prompt,
        config = types.GenerateContentConfig(
            response_mime_type = "application/json",
            temperature = 0.2,
        ),
    )
    return json.loads(response.text)

#== 文法検索機能 ==#
@app.post("/grammar_search")
def grammar_serch(item:GrammarSearchIn):
    return analyze_grammar(item.text,item.targetLang,item.explainLang,item.context)

#== 発音検索機能 ==#
@app.post("/pronounce")
def pronounce(item:PronounceIn):
    result = openai_client.audio.speech.create(
        model = "tts-1",#speed対応のTTSモデル
        voice = "alloy",#声の種類
        input = item.text,#読み上げる文章
        speed = item.speed,#速度
    )
    return Response(content = result.content,media_type ="audio/mpeg")#音声をmedia_type ="audio/mpeg"でmp3音声として返答する

#== リアルタイム会話機能 ==#
@app.websocket("/realtime")
async def realtime(websocket:WebSocket): #エンドポイントが起動後にこの関数のみ自動で処理される（ベースシステム）
    await websocket.accept()#接続を受け入れる
    first = await websocket.receive_text()#最初のメッセージを受け取り、first変数に入れる
    config = SessionConfig(**json.loads(first))
    start_watcher(config.watchPath)#UIで指定した作業フォルダを監視する。
    instructions = build_instructions(config)#指示文を作る

    gemini_config = {
        "response_modalities":["AUDIO"],#返事を音声にする
        "system_instruction":instructions,#指示文を入れる
        "input_audio_transcription":{"language_codes":[config.targetLang]},#自分の発言を文字起こしする
        "output_audio_transcription":{},#AIの発言を文字起こしする
        "tools":[CODE_TOOL],#コード分析ツール
    }
    print("文字起こし言語",gemini_config["input_audio_transcription"])
    async with client.aio.live.connect(model = MODEL,config = gemini_config) as session:
        audio_buffer = bytearray()#音声用のリスト

        async def frontend_to_gemini():
            try:
                while True:
                    raw = await websocket.receive_text()#メッセージを受け取る
                    msg = json.loads(raw)#辞書化して見れる形にする
                    if msg.get("type") == "input_audio_buffer.append":#フロントからの送信が音声である場合
                        pcm = base64.b64decode(msg["audio"])#メッセージの中の音声部分msg["audio"]を、生バイトに戻す
                        audio_buffer.extend(pcm)
                        await session.send_realtime_input(
                            audio = types.Blob(data=pcm,mime_type="audio/pcm;rate=16000")
                        )
            except WebSocketDisconnect:#切れたら止める
                pass

        async def gemini_to_frontend():
            user_text = ""#自分の発言を貯める
            ai_text = ""#AIの発言を貯める
            try:
                while True:
                    async for response in session.receive():
                        if response.tool_call:#コード分析関数の実行要求が来たか検知する
                            print("デバック")
                            print("デバックの中身",response.tool_call.function_calls)
                            responses = []#Geminiに結果を送信する

                            for fc in response.tool_call.function_calls:#実行要求を一つ一つ実行
                                print("デバック2")
                                result = await analyze_code(fc.args.get("request",""),config.targetLang)
                                print("analyze結果（デバック）",result)
                                if result["code"]:#返答にコードがあればフロントに送信
                                    await websocket.send_text(json.dumps({
                                        "type":"code_analysis",#フロント表示用
                                        "code":result["code"],
                                    }))
                                responses.append(types.FunctionResponse(
                                    id=fc.id,#どの実行要求に対する返事か
                                    name = fc.name,
                                    response={"result": result["summary"]},
                                ))
                                await session.send_tool_response(function_responses=responses)#Geminiに要約を返す
                                continue
                        if response.data is not None:#何か音声があれば以下を実行する
                            b64 = base64.b64encode(response.data).decode()#バイトをbase64に直す
                            await websocket.send_text(json.dumps({
                                "type":"response.output_audio.delta",
                                "delta":b64,
                            }))
                        sc = response.server_content
                        
                        if sc is None:#文字情報が無ければ、そのまま飛ばして継続
                            continue
                        if sc.input_transcription and sc.input_transcription.text:#そもそも文字起こしがあり、その中に文字があれば、自分の発言を貯める
                            user_text += sc.input_transcription.text
                            turn_id = str(time.time())#この発言のID
                            utterance_audio=bytes(audio_buffer)#この発言の音声をコピー
                            audio_buffer.clear()#次の発言用に空にする
                            await websocket.send_text(json.dumps({
                                    "type":"conversation.item.input_audio_transcription.completed",
                                    "transcript":user_text,
                                    "id":turn_id,
                            }))
                            asyncio.create_task(analyze_turn(user_text,utterance_audio,websocket,config,turn_id))

                        if sc.output_transcription and sc.output_transcription.text:#AIの発言に文字起こしがあり、その中に文字があれば、AIの発言を貯める
                            ai_text += sc.output_transcription.text
                            await websocket.send_text(json.dumps({
                                    "type":"response.output_audio_transcript.done",
                                    "transcript":ai_text,
                            }))
                        if sc.interrupted:#ユーザーが途中で割り込んだら
                            await websocket.send_text(json.dumps({
                                    "type":"interrupted",
                                    "transcript":ai_text,
                            })) 
                            ai_text=""#途中で切れたのでリセット

                        if sc.turn_complete:#一区切りが完了したら
                            await websocket.send_text(json.dumps({
                                    "type":"response.output_audio_transcript.finish",
                                    "transcript":ai_text,
                            }))
                            user_text = ""#リセットする
                            ai_text=""#リセットする
                            audio_buffer.clear()#AIの返事ぶんの音声を捨てる（次の発話をきれいに録るため）
            except Exception as e:
                print("gemini_to_frontend エラー",e) 




        task_a = asyncio.create_task(frontend_to_gemini())
        task_b = asyncio.create_task(gemini_to_frontend())
        await asyncio.wait({task_a, task_b}, return_when=asyncio.FIRST_COMPLETED)
        task_a.cancel()
        task_b.cancel()
