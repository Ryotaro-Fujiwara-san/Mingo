# Mingo

> **AI と話して、訂正されて、発音まで磨かれる、英会話練習 Web アプリ**

ロールプレイ形式の音声会話を AI と行いながら、**文法・表現の訂正**・**音素レベルの発音採点**・**AI 発言の文法解説**・**日本語からの英訳ヒント** をその場で受けられる、英語学習者のための AI スパーリングパートナーです。

---

## 1. プロジェクト概要

| 項目 | 内容 |
| --- | --- |
| **目的** | 「英語で会話したいけど相手がいない」「話せても合ってるか分からない」「発音が通じない」を一つのアプリで解決する |
| **ターゲット** | 中級〜上級英語学習者、ビジネス英会話を磨きたい社会人、英会話スクールの代わりを探している人、**英語面接対策をしたい就活生・転職活動者・MBA 受験者** |
| **提供形態** | Web アプリ（PC ブラウザ）、将来モバイル展開 |
| **コア技術** | OpenAI Whisper / GPT-5 / TTS + Azure AI Speech (Pronunciation Assessment) |
| **差別化** | 「ロールプレイ × 厳密採点 × 深い解説」を **1つに統合** したことが他にない（Speak は採点が雑、ELSA は会話がない、ChatGPT は学習向けじゃない） |

---

## 2. 主要機能（7つの柱）

### ① リアルタイム多人数音声会話（割り込み可）

**マイクをずっと ON にした状態の自然な会話**。録音ボタンは不要。AI の話の途中で割り込んでもOK。複数の AI キャラが登場し、AI 同士が会話して時々ユーザーに話を振る。

```
ユーザー: 「会社の会議シミュレーションをしたい。私は新入社員役」と指示
        │
        ▼
AI: 動的に登場人物を生成
   - Sarah (マネージャー、声: alloy)
   - Mike (エンジニア、声: echo)
   - ユーザー (新入社員)
        │
        ▼
[常時マイクON で会話開始]
Sarah: "Mike, what's the status on the new feature?"
Mike:  "It's about 80% done. There's an edge case I'm still..."
                                  ↑
                            ユーザーが話し始める
                                  ↓
[Mike の発話、割り込みで自動停止]
ユーザー: "Sorry, can I ask about the timeline?"
        │
        ▼
オーケストレーターが「次に誰が話すか」を判断
        │
Sarah: "Sure, the deadline is Friday. Mike, can you explain the risks?"
Mike:  "The main concern is..."
   ...
Sarah: "And [user-name], do you have any concerns from the QA side?"
                                  ↑
                       AI が自然にユーザーへ話を振る
        │
        ▼
ユーザーが応答 → 会話継続
```

**他のアプリにない 3つの特長**:
- ✅ **マイクON常時**：ボタン押下不要、ストレスフリー
- ✅ **割り込み可（barge-in）**：AI の発話途中で遮れる、人間の会話に近い
- ✅ **多人数AI**：AI 同士が会話、自然にユーザーに振る → **会議・面接・グループディスカッションの真のシミュレーション**

技術的には **OpenAI Realtime API** + **マルチエージェント・オーケストレーター** で実現。

### ② 文法・表現の自動訂正

```
ユーザー発話: "I want a coffee, one please."
        │
        ▼
GPT が「自然さ」と「文法」をチェック
        │
        ▼
画面に訂正版が表示:
   ❌ "I want a coffee, one please."
   ✅ "Could I have one coffee, please?"
       理由: "I want" は直接的すぎる。"Could I have ..." の方が丁寧で自然
```

**会話を止めずに**、横にそっと訂正が出る UX。

### ③ 音素レベル発音採点 + リンキング解析

```
ユーザー発話: "Could I have one coffee, please?"
        │
        ├──→ Azure AI Speech (Pronunciation Assessment)
        │       /k/ → 95点
        │       /ʊ/ → 78点（やや「ウ」寄り、英語の /ʊ/ をより緩めに）
        │       /θ/ → 該当なし
        │       Fluency 82 / Accuracy 88 / Completeness 100
        │
        └──→ GPT-5-audio (定性評価)
                「could I have の繋ぎがやや硬い。"クッダイ・ハヴ" のように
                  リエゾンさせるとネイティブ風」
        │
        ▼
画面に音素マップ + 改善アドバイス
```

「**スコア + 具体的にどう直すか**」までセット。

### ④ AI 発言の文単位 文法・イディオム解説

```
AI: "I'd be happy to help you with that."
        │
        │ ユーザーが文をクリック
        ▼
ポップアップで深掘り解説:

【翻訳】「喜んでお手伝いしますよ」

【文法構造】
   - I'd = I would の口語短縮
   - "would be happy to do" = 仮定法による丁寧表現
   - "help A with B" = 「A の B を手伝う」

【イディオム / 慣用表現】
   "I'd be happy to" はビジネス英語の定番フレーズ。
   "Sure" よりフォーマル、"I would love to" より中立的。

【類似表現の使い分け】
   - I'd be glad to ...    （glad は感情寄り）
   - I'd love to ...        （かなり前向き、社交的）
   - I'd be happy to ...    （ニュートラル、ビジネス向き） ★これ

【発音注意】
   "I'd be" は /aɪd bi/ → 速く発音すると /aɪbi/ に近づく
```

「**辞書ではなく英語の先生**」の深さ。Trancy など他ツールは出来ない。

### ⑤ 日本語 → 英語ヒント（言いたいことサポート）

```
ユーザー（テキスト入力欄）: 「もう少しゆっくり喋ってもらえる？」
        │
        ▼
GPT が複数の英訳案 + 文法・イディオムを提示:

✅ 自然な言い方（3パターン）:
   1. "Could you speak a little more slowly, please?"
       └─ もっとも丁寧。"a little more + 形容詞" の比較級の使い方
   2. "Could you slow down a bit?"
       └─ カジュアル。"slow down" は句動詞
   3. "Sorry, could you say that again more slowly?"
       └─ 聞き取れなかった含意つき

⚠️ 避けたい直訳:
   ✗ "Can you speak slowly more?" → 語順がおかしい
   ✗ "Speak slowly please" → 命令的、失礼に聞こえる
```

会話中に詰まったときの **"ライフライン"** 機能。

### ⑥ 単語クリック → 発音再生

```
画面に表示された任意の単語をクリック
        │
        ▼
- 即座に発音（OpenAI TTS / Azure Neural Voice）
- IPA 表記: /ˈkɒfi/
- 強勢の位置を視覚的に表示
- 「米国式」「英国式」切り替え可能
```

知らない単語の発音を **その場で確認** できる。

### ⑦ レジュメ / プロフィール提出 → AI 面接官モード

```
ユーザー: レジュメ・README・LinkedIn 抜粋などをテキストで提出
         「ソフトウェアエンジニア職の英語面接を練習したい」と指示
        │
        ▼
AI: 提出された内容を読み込んで質問プランを生成
   - 自己紹介系
   - レジュメから掘る技術深掘り質問
   - 行動面接 (STAR形式の質問)
   - 状況対応質問
   - 逆質問の練習
        │
        ▼
1問ずつ AI が質問 → ユーザーが音声で回答
   - 機能①②③ がそのまま動作
     (会話・訂正・発音採点)
   - AI が追撃質問 (follow-up) を投げる
   - 質問の難易度を段階的に上げる
        │
        ▼
面接終了後: 総合フィードバックレポート
   - 各回答ごとの強み/弱み
   - 「STAR フレームワークで答え直すなら」のサンプル回答
   - 発音傾向の集計 (例: /θ/ がいつも /s/ になってる)
   - 文法/表現の頻出ミスまとめ
   - 改善のための練習プラン提案
```

**「英語面接で話せない」「面接対策の相手がいない」** という痛みを直接解決。  
**就活生・転職活動中の社会人・MBA 受験者** に強く刺さる。B2B（人材紹介会社・キャリアスクール）の販売チャネルにもなる。

---

## 3. システム構成

```
┌────────────────────────────────────────────────────┐
│  フロントエンド: React + Vite                       │
│                                                     │
│  - ロールプレイ画面 + 登場人物カード                  │
│  - マイク常時ON (getUserMedia + WebRTC)             │
│  - AI 音声のストリーミング再生                       │
│  - 割り込み検出 (VAD: Voice Activity Detection)     │
│  - 訂正・採点・解説のオーバーレイ表示                │
│  - 日本語→英訳ヒント入力欄                          │
└─────────────────┬──────────────────────────────────┘
                  │ WebSocket / WebRTC
                  │
┌─────────────────▼──────────────────────────────────┐
│  バックエンド: Python + FastAPI                     │
│                                                     │
│  /ws/conversation   会話セッションのストリーミング   │
│      ├─ OpenAI Realtime API ← 中核                  │
│      │     - 音声入出力ストリーム                     │
│      │     - 割り込み制御 (barge-in)                 │
│      │     - 低遅延                                   │
│      ├─ オーケストレーター (Python)                   │
│      │     - 複数の AI ペルソナを管理                 │
│      │     - 「次に誰が話すか」を判断                  │
│      │     - ユーザー発話時の応答者を選択              │
│      ├─ Azure Speech ← 音素採点 (ターン終了時に発動)  │
│      └─ GPT-5 ← 訂正・解説・ヒント (非同期)           │
│                                                     │
│  /api/explain         文単位の解説                  │
│  /api/hint            日本語→英訳ヒント             │
│  /api/word_audio      単語の発音再生用              │
│  /api/interview_start  レジュメ→面接プラン生成      │
│  /api/interview_report 面接終了後フィードバック     │
└────────────────────────────────────────────────────┘
```

### フロントエンド
| 項目 | 内容 |
| --- | --- |
| 技術スタック | React + Vite + TypeScript |
| 音声入力 | MediaRecorder API（ブラウザ録音） |
| 音声出力 | HTML5 Audio + Web Audio API |
| UI | Tailwind CSS（予定） |

### バックエンド
| 項目 | 内容 |
| --- | --- |
| 技術スタック | Python + FastAPI + Uvicorn |
| 主な API | OpenAI (Whisper / GPT-5 / TTS), Azure AI Speech |
| キャッシュ | ローカルJSON（個人開発時）→ Supabase（製品化フェーズ） |

---

## 4. データ管理

| 項目 | 内容 |
| --- | --- |
| **会話履歴** | セッション単位で保存（Phase2 で永続化） |
| **ユーザー設定** | レベル、ターゲットアクセント、シナリオ履歴 |
| **保管場所** | 個人開発: `cache/` フォルダ / 製品化後: Supabase |

製品化フェーズ（後述）で **Supabase (PostgreSQL)** に移行。

---

## 5. ファイル構成（予定）

```
mingo/
│
├── frontend/                    # React + Vite
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx      会話表示
│   │   │   ├── MicButton.tsx       録音ボタン
│   │   │   ├── CorrectionCard.tsx  訂正表示
│   │   │   ├── PronunciationView.tsx  音素スコア表示
│   │   │   ├── ExplainPopup.tsx    AI発言クリック解説
│   │   │   ├── HintBox.tsx         日本語→英訳ヒント
│   │   │   └── WordTooltip.tsx     単語ホバー/クリック発音
│   │   ├── hooks/
│   │   │   └── useRecorder.ts
│   │   └── api/
│   │       └── client.ts           バックエンド呼び出し
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── backend/                     # Python FastAPI
│   ├── main.py                  FastAPI エントリ + ルーティング
│   ├── ai_engine.py             Whisper / GPT / Azure 呼び出しの中核
│   ├── prompts.py               プロンプトテンプレート集
│   ├── tts.py                   TTS ラッパー
│   ├── pronunciation.py         Azure Speech 連携
│   ├── requirements.txt
│   ├── .env.example
│   └── cache/                   一時キャッシュ（自動生成）
│
├── README.md
└── .gitignore
```

---

## 6. 通信フロー例（リアルタイム多人数会話）

```
[セッション開始]
[1] frontend が WebSocket で /ws/conversation に接続
[2] backend が OpenAI Realtime API へ接続、システムプロンプトを設定
    (登場人物・シナリオ・割り込み許可フラグ)
[3] backend が Sarah (AI_1) の最初のセリフを生成 → 音声ストリーム開始
[4] frontend が音声を順次再生

[会話の継続]
Sarah が話し中、Mike (AI_2) も話す番を待つ
   │
   ▼ オーケストレーター: Sarah → Mike へバトン
Mike が応答を生成 → 音声ストリーム

[ユーザーの割り込み]
[5] frontend の VAD がユーザーの発話を検出
[6] frontend が backend へ「割り込み開始」通知
[7] backend が Realtime API へ "cancel" を送信 → AI 発話即停止
[8] ユーザーの音声がストリームで backend に流れる
   ├─ Realtime API が音声→テキストへリアルタイム変換
   ├─ オーケストレーターが「ユーザーに最後に話しかけたのは誰か」を確認
   └─ そのキャラが応答を生成
[9] AI 応答が音声ストリームで返り、frontend で再生

[非同期処理: 訂正・採点]
[10] ユーザーの発話が完了したらバックグラウンドで:
     - GPT-5: 文法・表現の訂正生成
     - Azure Speech: 音素スコア計算
[11] 結果を WebSocket でフロントへ push
[12] frontend がオーバーレイで表示（会話は止めない）
```

---

## 7. 開発ロードマップ

開発は **「個人プロトタイプ」→「製品化」** の 2 フェーズ。

### フェーズ1: 個人プロトタイプ

| Step | 内容 | 状態 |
| --- | --- | --- |
| **準備** | フォルダ作成、Vite + React + FastAPI のひな型、OpenAI Realtime API のアクセス確認 | ⬜ |
| **Step 1** | **1対1のリアルタイム音声会話** を実装：OpenAI Realtime API + WebSocket で、マイク常時ON + AI 応答音声ストリーム + 割り込み (barge-in) 対応。シナリオは固定文字列で OK | ⬜ |
| **Step 2** | **多人数AIオーケストレーター**：複数の AI ペルソナ（声・性格が違うキャラ）を作成し、「次に誰が話すか」を判断するロジックを実装。AI 同士の会話 + ユーザーへの自然な振り出しを実現 | ⬜ |
| **Step 2.5** | **シナリオ動的生成**：ユーザーが「会社の会議」「カフェで注文」のようなお題をテキストで指示 → AI が登場人物・状況・最初のセリフを生成 | ⬜ |
| **Step 3** | **文法・表現の訂正機能**：ユーザー発話を GPT に渡し、自然さと文法をチェック → 訂正版を画面表示 | ⬜ |
| **Step 4** | **AI 発言の文単位解説**：AI 発言をクリックすると、訳・文法・イディオム・類似表現・発音注意までセクション分けで表示 | ⬜ |
| **Step 5** | **日本語 → 英語ヒント**：テキスト入力で日本語の言いたいことを書く → GPT が複数の英訳案 + 文法・イディオム解説を返す | ⬜ |
| **Step 6** | **単語クリック発音再生**：画面のどの単語をクリックしても、その単語だけを TTS で再生 + IPA 表示 | ⬜ |
| **Step 7** | **音素レベル発音採点**：Azure AI Speech (Pronunciation Assessment) で音素ごとのスコアと正解 IPA を取得 + GPT-5-audio で自然さ・リンキングの定性評価を加えて合成表示 | ⬜ |
| **Step 8** | **AI 面接官モード**：レジュメ/プロフィールを提出 → AI が質問プランを生成して順に質問 → ユーザー回答 → AI が追撃 → 終了後に総合フィードバックレポート（強み/弱み、STAR形式の改善サンプル、発音傾向、文法ミス集計） | ⬜ |
| **Step 9** | UI ポリッシュ・レイテンシ削減・キャッシュ整備 | ⬜ |

### フェーズ2: 製品化（マルチユーザー対応）

| Step | 内容 | 状態 |
| --- | --- | --- |
| **Step 10** | **ユーザーアカウント・認証**を Supabase Auth で実装（Google ログイン / メール+パスワード） | ⬜ |
| **Step 11** | **会話履歴・進捗ダッシュボード**：セッション保存、音素別の上達グラフ、訂正された誤りパターン集計、面接練習履歴 | ⬜ |
| **Step 12** | **課金システム（Stripe）**：無料 / Pro / Pro Plus / Interview Pack（面接特化）。OpenAI / Azure コストをユーザーが支払う形に | ⬜ |
| **Step 13** | **デプロイ・本番運用**：Vercel (frontend) + Render/Railway (backend) + Supabase (DB)。CI/CD（GitHub Actions） | ⬜ |

### 将来検討（MVP 後）

| 課題 | 内容 |
| --- | --- |
| モバイルアプリ | iOS / Android (React Native or Flutter)。会話練習はモバイル親和性が高い |
| B2B (法人向け) | 企業の英語研修用、複数アカウント管理、進捗レポート機能 |
| B2B (人材・教育) | 人材紹介会社 / キャリアスクール / MBA予備校への「面接対策パック」販売。Step 8 の面接官モードを軸に法人契約 |
| 動画教材連携 | 旧 Mingo (YouTube字幕翻訳) の機能を取り込み、動画のセリフをそのままロールプレイ素材に |
| 多言語対応 | 英語以外の言語学習（中国語、韓国語、スペイン語など） |

---

## 8. 必要な API キー・サービス

### フェーズ1（プロトタイプ）

| サービス | 用途 | 備考 |
| --- | --- | --- |
| **OpenAI Realtime API** (`gpt-realtime` 系) | リアルタイム音声会話の中核：常時マイクON / 割り込み (barge-in) / 低遅延ストリーミング音声入出力 / 複数声切替 | OpenAI API キー。Step 1 から必須。**Realtime は他APIより高コスト**（数倍）なので、Step 8 移行時にキャッシュ・最適化重要 |
| **OpenAI Whisper API** (`whisper-1`) | 単独の音声→テキスト（Realtime 範囲外の用途、例：ユーザー発話の事後解析） | OpenAI API キー |
| **OpenAI GPT-5** | 訂正・解説・英訳ヒント・オーケストレーター判断・面接質問プラン | 同上 |
| **OpenAI TTS** (`tts-1` / `tts-1-hd`) | 単語クリック発音、面接フィードバック朗読など Realtime 範囲外 | 同上 |
| **OpenAI GPT-5-audio** (`gpt-5-audio` 系) | 発音の定性評価（リンキング等） | 同上 |
| **Azure AI Speech** (Pronunciation Assessment) | 音素レベルスコアリング、正解IPA、Fluency/Accuracy/Completeness | 別途 Azure サブスクリプション。月 5 時間まで無料枠あり |
| **FastAPI / Uvicorn** | バックエンドサーバー | OSS（無料） |
| **React + Vite** | フロントエンド | OSS（無料） |

### フェーズ2（製品化）

| サービス | 用途 | 備考 |
| --- | --- | --- |
| **Supabase** | DB（PostgreSQL）+ 認証 + Storage | 無料枠 500MB DB / 5GB Storage |
| **Stripe** | サブスクリプション課金 | テストモードは無料、本番は売上の 3.6% 程度 |
| **Vercel** | フロントエンド・ホスティング | 個人利用は無料 |
| **Render / Railway / Fly.io** | バックエンド・ホスティング | $7/月 程度から |

---

## 9. ライセンス / 開発者

| 項目 | 内容 |
| --- | --- |
| **開発者** | 藤原 遼太郎 |
| **所在地** | 〒722-0022 広島県尾道市栗原町5835-1 |
| **連絡先** | expo70314911@gmail.com |
| **ライセンス** | 個人開発・学習用途（商用利用は要相談） |

---

## 10. これまでの経緯

このリポジトリは元々 **「YouTube 字幕翻訳 + クリック解説」** の Chrome 拡張機能として開発を開始しました（旧 Mingo）。Step 1 まで実装し、Python による音声DL → Whisper → 翻訳 → クリック解説の CLI まで動作確認済みです。

その後、市場分析と機能の差別化検討を行った結果、

- 字幕翻訳カテゴリには Trancy / Language Reactor などの強力な競合が既に存在し、**真っ向勝負は不利**
- 一方で **「ロールプレイ会話 × 訂正 × 音素レベル発音採点」** を統合したサービスは存在せず、痛みの強度も高い（発音・会話練習は「便利」ではなく「不安解消」レベルの需要）

と判断し、**AI 英会話練習アプリへピボット**しました。

旧 Mingo（字幕翻訳）のコードは [Mingo-legacy](https://github.com/Ryotaro-Fujiwara-san/Mingo-legacy) リポジトリに保存しています。Whisper / GPT 連携などのコードは新 Mingo にも転用予定です。
