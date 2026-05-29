# Mingo backend - FastAPI エントリポイント
#
# 提供するエンドポイント:
#   GET    /                     動作確認
#   GET    /health               ヘルスチェック
#   GET    /api/memo             メモ一覧
#   POST   /api/memo             メモ追加
#   DELETE /api/memo/{memo_id}   メモ削除
#   POST   /api/expression_hint  メモから「今使える表現」をサジェスト

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# .env を読み込む（OPENAI_API_KEY など）
from dotenv import load_dotenv
load_dotenv()

import memo  # メモ機能 + ヒント生成（memo.py）


# ════════════════════════════════════════════════
# FastAPI アプリのインスタンスを作る
# ════════════════════════════════════════════════
app = FastAPI(
    title="Mingo Backend",
    description="AI 英会話練習プロダクト Mingo のバックエンドAPI",
    version="0.1.0",
)

# ── CORS: Vite 開発サーバー(localhost:5173)からの呼び出しを許可 ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════
# 動作確認用
# ════════════════════════════════════════════════
@app.get("/")
def root():
    return {"message": "Hello from Mingo backend!"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ════════════════════════════════════════════════
# メモ機能 (/api/memo)
# ════════════════════════════════════════════════
class MemoIn(BaseModel):
    text: str          # 覚えたい単語・表現（必須）
    note: str = ""     # 意味やメモ書き（任意）
    source: str = ""   # "ai" / "self" など（任意）


@app.get("/api/memo")
def get_memos():
    return {"memos": memo.list_memos()}


@app.post("/api/memo")
def create_memo(body: MemoIn):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text は必須です")
    return memo.add_memo(body.text, body.note, body.source)


@app.delete("/api/memo/{memo_id}")
def remove_memo(memo_id: str):
    if not memo.delete_memo(memo_id):
        raise HTTPException(status_code=404, detail="そのメモは見つかりません")
    return {"deleted": memo_id}


# ════════════════════════════════════════════════
# ヒントボタン (/api/expression_hint)
# ════════════════════════════════════════════════
class HintIn(BaseModel):
    context: str = ""  # 直近の会話の流れ
    max: int = 3       # 最大サジェスト数


@app.post("/api/expression_hint")
def expression_hint(body: HintIn):
    try:
        suggestions = memo.suggest_hints(body.context, max_n=body.max)
    except memo.MissingAPIKey as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"suggestions": suggestions}
