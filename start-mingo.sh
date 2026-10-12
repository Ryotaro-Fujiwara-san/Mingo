#!/usr/bin/env bash
# Mingo を Ubuntu (WSL) で起動する。Ctrl+C かウィンドウを閉じると両方止まる
cd "$(dirname "$0")" || exit 1

if [ ! -f backend/.env ]; then
  echo "backend/.env がありません。APIキーを書いた .env を置いてください。"
  read -r -p "Enter で終了"
  exit 1
fi

cleanup() {
  trap - EXIT INT TERM HUP
  echo "Mingo を終了します..."
  kill 0
}
trap cleanup EXIT INT TERM HUP

(cd backend && source .venv/bin/activate && exec uvicorn main:app) &
(cd frontend && exec npm run dev -- --strictPort) &

echo "Mingo 起動中: http://localhost:5173"
echo "終わるときはこのウィンドウを閉じるか Ctrl+C を押してください。"
wait
