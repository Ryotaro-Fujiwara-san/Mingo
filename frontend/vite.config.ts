import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API = "http://localhost:8000"
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {//この窓口宛てのリクエストは、FastAPIに転送する
      "/memo": API,
      "/hint": API,
      "/interaction": API,
      "/dashboard": API,
      "/delete": API,
      "/grammar_search": API,
      "/pronounce": API,
      "/health": API,
      "/realtime": { target: API, ws: true },//WebSocketも転送する
    },
  },
})
