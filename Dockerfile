# ===== 1段目：Reactの画面をビルドする ===== #
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ===== 2段目：FastAPIを動かす箱を作る ===== #
FROM python:3.14-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libssl3 libasound2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]