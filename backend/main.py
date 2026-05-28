# Mingo backend - FastAPI エントリポイント
# Step 0: 最小の Hello World サーバー
# 後で WebSocket /ws/conversation や 各種 /api/... を追加していく

from fastapi import FastAPI

# .env を読み込む (まだ使わないけど準備)
from dotenv import load_dotenv
load_dotenv()


# ════════════════════════════════════════════════
# FastAPI アプリのインスタンスを作る
# ════════════════════════════════════════════════
app = FastAPI(
    title="Mingo Backend",
    description="AI 英会話練習プロダクト Mingo のバックエンドAPI",
    version="0.0.1",
)


# ════════════════════════════════════════════════
# ルート (/) にアクセスしたら hello を返す
# ════════════════════════════════════════════════
@app.get("/")
def root():
    return {"message": "Hello from Mingo backend!"}


# ════════════════════════════════════════════════
# /health に GET したら "ok" を返す
# (サーバーが生きてるかチェック用、運用で重要)
# ════════════════════════════════════════════════
@app.get("/health")
def health():
    return {"status": "ok"}
