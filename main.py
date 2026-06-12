from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()


@app.get("/")  # トップページ：index.html を返す（フロントもバックも同じサーバー＝CORS不要）
def index():
    return FileResponse("index.html")


@app.get("/health")  # 動作確認用：/health に GET が来たら {"status":"ok"} を返す
def health():
    return {"status": "ok"}
