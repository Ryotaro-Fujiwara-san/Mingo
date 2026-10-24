# Mingo システムアーキテクチャ

[English version](architecture.en.md)

## 全体構成

```mermaid
flowchart LR
    learner["学習者のブラウザー<br/>React + TypeScript<br/>マイク・音声再生"]
    cognito["Amazon Cognito<br/>OIDCログイン・JWT発行"]

    subgraph aws["AWS 本番環境"]
        ingress["ECS Express Mode<br/>HTTPS / WebSocket"]
        app["ECS task（1 task）<br/>Docker container<br/><br/>FastAPI<br/>REST API・WebSocket<br/>JWT検証・日次利用上限<br/>React静的ファイル配信"]
        sqlite[("SQLite memo.db<br/>メモ・習得記録・利用回数")]
        efs["Amazon EFS<br/>永続ボリューム"]
        secrets["AWS Secrets Manager<br/>外部APIキー"]
        ecr["Amazon ECR<br/>Docker image"]
        actions["GitHub Actions<br/>テスト・ビルド・デプロイ"]
    end

    gemini_live["Google Gemini Live API<br/>音声会話・文字起こし"]
    gemini["Google Gemini API<br/>文法・メモ分類・ヒント"]
    openai["OpenAI API<br/>埋め込み・音声合成"]
    azure["Azure AI Speech<br/>発音評価"]

    learner <-->|"ログイン・JWT取得"| cognito
    learner -->|"HTTPS: REST + JWT"| ingress
    learner <-->|"WSS: 音声・会話イベント"| ingress
    ingress --> app
    app <-->|"読み書き"| sqlite
    sqlite ---|"EFS mount<br/>/mnt/mingo-data"| efs
    secrets -.->|"環境変数として注入"| app

    app <-->|"音声ストリーミング"| gemini_live
    app <-->|"テキスト生成"| gemini
    app <-->|"埋め込み・TTS"| openai
    app <-->|"発音評価"| azure

    actions -->|"AWS OIDC認証後にpush"| ecr
    actions -->|"サービス更新"| ingress
    ecr -->|"イメージ取得"| app

    subgraph local["ローカル開発時のみ（任意）"]
        local_app["ローカル実行中のFastAPI"]
        files["開発PC上の作業ファイル"]
        claude["Claude Agent SDK<br/>読み取り専用のコード分析"]
    end
    app -->|"JWKS公開鍵でJWT検証"| cognito
    local_app -.->|"ENABLE_CODE_ANALYSIS=true"| claude
    claude -->|"Read / Grep / Glob"| files
```

## 主なリクエストの流れ

1. ブラウザーがCognitoでログインし、JWTを取得します。REST APIではAuthorizationヘッダー、会話WebSocketでは接続時のトークンをFastAPIが検証します。
2. React画面は同じECS Express ModeのURLから配信されます。通常のAPI呼び出しはHTTPS、音声会話はWebSocketでFastAPIに接続します。
3. FastAPIは会話音声をGemini Live APIへ中継し、会話中の文法チェックやヒント生成などを各AI APIに依頼します。発音評価ではAzure AI Speechを使用します。
4. メモ、習得状況、API利用回数はSQLiteに保存します。本番ではSQLiteファイルをEFS上に置き、タスク数を1に制限します。
5. GitHub Actionsはバックエンドテストの後、DockerイメージをECRにpushし、ECS Express Modeのサービスを更新します。

## 補足

- ECSタスク定義からEFSを`/mnt/mingo-data`にマウントし、`MEMO_DB_PATH=/mnt/mingo-data/memo.db`を指定します。
- 外部APIキーはSecrets Managerで管理し、タスクの環境変数としてアプリに渡します。
- コード分析機能はローカル開発時のみの任意機能です。`ENABLE_CODE_ANALYSIS=true`の場合にClaude Agent SDKが開発PC上の作業ファイルを読み取ります。本番の通常経路には含まれません。
