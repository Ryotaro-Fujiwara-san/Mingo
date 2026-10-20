# ECS Express ModeでSQLiteをEFSに永続化する

この手順では、既存のSQLiteデータは引き継がず、空のDBでEFS運用を開始します。既存データが必要な場合は、別途バックアップ・移行を行ってください。

## 1. EFSを準備する

1. ECSサービスと同じVPCにEFSファイルシステムを作り、サービスが利用する各AZにマウントターゲットを作成します。
2. ECSタスクのセキュリティグループからEFSのセキュリティグループへNFS/TCP `2049` を許可します。EFS側はタスクのセキュリティグループからのNFSだけを許可します。
3. `/mingo` をルートにするEFSアクセスポイントを作成します。アクセスポイントが強制するPOSIXユーザー/グループとディレクトリ権限は、アプリが読み書きできる値（例: UID/GID `10001`、モード `0770`）にします。
4. この方針では既存の `memo.db` はコピーしません。EFSにDBファイルがない状態で初回起動すると、アプリが空のDBと初期テーブルを作成します。
5. GitHubリポジトリの **Settings → Secrets and variables → Actions → Variables** に次の変数を登録します。
   - `EFS_FILE_SYSTEM_ID`: EFSファイルシステムID
   - `EFS_ACCESS_POINT_ID`: EFSアクセスポイントID

ECSタスクはEFSマウント設定を使って `/mnt/mingo-data` をマウントし、`MEMO_DB_PATH=/mnt/mingo-data/memo.db` を指定します。デプロイworkflowは現在のECSタスク定義を土台に新しいイメージとEFS設定を登録するため、現在の環境変数、Secrets Manager参照、実行ロールなどを引き継ぎます。

## 2. 既存DBを引き継がないことを確認する

EFS作成だけでは現在のデータは移りません。この手順では、デプロイ後に既存DBの内容（学習中メモ、習得済み記録、利用回数など）は引き継がれず、利用者には空のDBが見えます。必要なデータが後から必要になる可能性があるなら、デプロイを止めて先にバックアップ方法を解決してください。

ECS Execを有効にする設定は、新しいタスクを起動した後でのみ使えます。現在のコンテナ内のDBを残すには別途退避が必要ですが、この手順では行いません。

## 3. デプロイする

EFSアクセスポイントが `Available` で、EFS変数とネットワーク設定が正しいことを確認してからデプロイします。pushによる自動デプロイには `AUTO_DEPLOY_ENABLED=true` が必要ですが、Actionsの **Run workflow** からの手動実行ではこのフラグは不要です。workflowは未設定のEFS変数を検出するとデプロイ前に失敗します。アプリはEFSマウントがなければ起動しません。EFS上で一度DBを初期化した後、DBファイルが消えた場合も起動を拒否します。

SQLiteをEFS上で使う間は `max-task-count: 1` とし、水平スケールさせません。定期的にDBのバックアップを別の保存先に取り、復元テストを行ってください。SQLite/EFSはRDSのようなDBサービスではないため、高い同時書き込みや複数タスク運用が必要になった場合はRDSなどへの移行を検討します。

## デプロイ権限

GitHub Actionsが利用するIAMロールには、Expressサービス/タスク定義の読み取り (`ecs:DescribeExpressGatewayService`、`ecs:DescribeTaskDefinition`)、新しいタスク定義の登録 (`ecs:RegisterTaskDefinition`)、Expressサービスの更新 (`ecs:UpdateExpressGatewayService`) が必要です。タスク定義が参照する実行ロール/タスクロールに対する `iam:PassRole` も必要です。
