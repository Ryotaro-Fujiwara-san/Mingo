from fastapi import FastAPI,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(#あるアドレスのページ（localhost:5173）が、別のアドレス（127.0.0.1:8000）を勝手に呼び出すのは危険かもしれないので、呼ばれる側（バックエンド）が「このアドレスからならOK」と許可を出していなければ、ブラウザがブロックする。
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/health")#/healthにGETが来たら下の関数を呼ぶ
def health():
    return{"status":"ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket:WebSocket):#websocketという名前で“WebSocket回線” を1つ受け取ります
    await websocket.accept()
    try:
        while True:#つなぎっぱなしでずっと継続
            data = await websocket.receive_text()#相手が話すのを待って、言葉を受け取る
            await websocket.send_text("サーバーが受け取りました:"+data)#受け取った言葉を頭に文に付けて返す
    except WebSocketDisconnect:pass#相手がタブを閉じたとき、エラーで落ちないようにする
