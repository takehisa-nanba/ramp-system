# 旧slice2互換migration 本番作業runbook (実配置確定版)

本書は、旧slice2互換migrationの本番適用に必要な実配置構成、停止・排出手順、再開手順、最小実HTTP検証、ロールバック条件、および運用体制を確定した作業runbookである。

> [!NOTE]
> **技術リハーサル判定: 技術GO（合格済）**
> 専用DBを用いたデータ保持、互換DDL、バックアップ・実restore検証はすべて合格しています。
> 本書では、現在の小規模・単一Windows環境に最適化した運用手順を定めています。

---

## 1. 実配置構成の棚卸し結果

現在の実環境（Windowsローカル実行環境）およびリポジトリ構成に基づく実態です。「存在しない」コンポーネントも明示しています。

| コンポーネント | 実稼働・構成状態 | 検出元 / 根拠 | 移行時の運用上の扱い |
|---|---|---|---|
| **Webアプリプロセス** | Flask 3.1.2 (`create_app(Config)`)。手動起動型（常駐プロセスなし） | [run.py](file:///c:/Users/nanba/Desktop/ramp-system/backend/run.py) | `python backend/run.py` で手動起動・停止 |
| **Reverse Proxy** | **存在しない**（Nginx / Caddy / ALB / IIS等は未構成） | ポート80/443確認 | プロキシ制御は行わず、**Webプロセス停止（ポート5000解放）で直接トラフィック遮断** |
| **Application Server** | **存在しない**（Gunicorn / Waitress 等の専用WSGI未導入） | [requirements.txt](file:///c:/Users/nanba/Desktop/ramp-system/backend/requirements.txt) | Werkzeug内蔵サーバー (`python backend/run.py`) を直接実行 |
| **Worker / Scheduler**| **存在しない**（Celery / RQ / APScheduler / タスクスケジューラなし）| コード・OS検索確認 | 停止・再開対象外（スキップ） |
| **Cron / 定期処理** | **存在しない**（定期バッチスクリプトなし） | リポジトリ検索確認 | 停止・再開対象外（スキップ） |
| **外部連携** | Google Gemini API (`GEMINI_API_KEY`) のみ（同期HTTP呼出し） | [config.py](file:///c:/Users/nanba/Desktop/ramp-system/backend/config.py) | Webアプリ停止により外部呼出しも自動遮断 |
| **DB接続元** | ローカルPostgreSQL (`postgresql-x64-17`) | [.env](file:///c:/Users/nanba/Desktop/ramp-system/.env) | 停止前に `pg_stat_activity` で接続0件を確認 |
| **プロセス管理方式** | DBのみWindowsサービス。Webアプリは**プロセス管理ツールなし** (手動実行) | サービス一覧確認 | 手動でプロセスの起動・停止を管理 |
| **ログ出力先** | 標準出力 (stdout/stderr) のみ（ファイル未構成） | `logging.basicConfig` | コンソール出力を保護領域ファイルへ記録 |
| **Health Check** | **存在しない**（専用 `/health`, `/api/health` なし） | ルーティング確認 | GET `/api/users` 等の主要API疎通で代用 |
| **Restart Policy** | **存在しない**（プロセス監視なし） | 構成全域確認 | 異常停止時は手動介入 |

---

## 2. Git / Worktree の現在地と作業ディレクトリ

| 作業ツリー / パス | ブランチ | コミット | 役割と位置づけ |
|---|---|---|---|
| **メイン作業ツリー**<br/>`c:\Users\nanba\Desktop\ramp-system` | `feature/job-retention-slice2` | `6d8b343` | **旧システム（現在の稼働ベース・本番ロールバック対象artifact）** |
| **適用・検証作業ツリー**<br/>`C:/Users/nanba/.codex/worktrees/retention-core-phase1/ramp-system` | `codex/slice2-release-rehearsal` | `08c5726` | **新機能・互換マイグレーション・C1/C4検査スクリプトを含む新コードベース（適用候補）** |

> [!IMPORTANT]
> **作業ディレクトリに関する重要規則**:
> 1. `backend/tests/check_slice2_release.py`（C1/C4検査）および `backend/migrations/slice2_compat`（互換マイグレーション）は、**新コード（`codex/slice2-release-rehearsal` ブランチ）** にのみ存在します。
> 2. したがって、停止中検査・マイグレーション・新アプリ起動は、**新コード側を作業ディレクトリとして実行**（またはメインツリーへ新コードをチェックアウト/マージして実行）します。
> 3. ロールバック時は、**旧コード（`6d8b343`）側を作業ディレクトリとして起動・切戻し**を行います。

---

## 3. 資格情報および接続情報の保護規定

> [!IMPORTANT]
> **パスワード・接続文字列のログ直書きは厳格に禁止します。**
> - DB接続情報はすべて保護された環境変数ファイル (`$ReleaseEnvFile`) または `DATABASE_URL` から読み込みます。
> - ログ、作業記録、コンソール出力にパスワード、APIキー、個人情報、クエリパラメータを含めてはなりません。
> - Runbook内のコマンド例では、実際の資格情報を含まない変数参照 (`$DATABASE_URL`, `$DB_USER` 等) を使用します。

---

## 4. DB環境メタデータと差分確認

本番候補DBの実機検査値と、リハーサル検証環境の差分照合結果です。

| 項目 | 本番候補DB設定 | リハーサル検証環境 | 判定 |
|---|---|---|---|
| **PostgreSQL Version** | 17.10 on x86_64-windows | 17.10 (同一クラスタ) | **差分なし (合致)** |
| **Database Owner** | 設定ロール (`$DB_USER`) | 設定ロール | **差分なし** (※restore時は `--no-owner` のため所有権付与が必須) |
| **Schema Owner / ACL** | 設定ロール (`UC`) | 設定ロール | **差分なし** |
| **Role / Privileges** | Login=True, CreateDB=True | 同一 | **差分なし** |
| **Encoding** | `UTF8` | `UTF8` | **差分なし (合致)** |
| **Locale** | `Japanese_Japan.utf8` | `Japanese_Japan.utf8` | **差分なし (合致)** |
| **Timezone** | `Asia/Tokyo` (JST) | `Asia/Tokyo` | **差分なし (合致)** |
| **Installed Extension** | `plpgsql (1.0)` のみ | `plpgsql (1.0)` | **差分なし (合致)** |
| **Default Tablespace** | `pg_default` | `pg_default` | **差分なし (合致)** |
| **Connection Limit** | `-1` (unlimited, max=100) | 同一 | **差分なし** |
| **lock_timeout** | `0` (サーバーデフォルト無制限) | セッション `10s` 指定 | **運用必須**: migrationセッションで明示的に `SET lock_timeout = '10s'` を設定 |
| **statement_timeout** | `0` (サーバーデフォルト無制限) | セッション `120s` 指定 | **運用必須**: migrationセッションで明示的に `SET statement_timeout = '120s'` を設定 |

---

## 5. ロールバック基準と復旧方針 (時点別マトリクス)

> [!WARNING]
> **公開再開後に新規書込みが発生した場合の自動restoreは絶対禁止です。**
> 新規書込みが存在する状態で旧backupへ単純restoreすると、再開後の業務データが永久に消失します。

| 作業時点 | 発生事象 / 判定条件 | ロールバック方針 | 具体的手順 |
|---|---|---|---|
| **1. migration開始前** | 停止失敗、残存接続あり、backup取得/検証失敗、source不一致、復旧締切到達 | **restore不要** | DBは未変更。旧Webアプリをそのまま起動して再開。 |
| **2. migration実行中** | DDLエラー、lock/statement timeout、スクリプト強制終了 | **TX rollback** | 単一トランザクション実行のため自動巻き戻し。`alembic_version` が `f8e31a7c49b2` であること、C1 source検査合格を確認。 |
| **3. migration直後** | `alembic_version` 不正、target schema不一致、制約/FK/sequence異常 | **新規復旧DBへrestore** | アプリ未起動。直前backupを別名新規DB (`ramp_db_recovery`) へrestoreし、アプリ接続先を切り替えて旧アプリ起動。 |
| **4. APIスモーク中 (内部)**| 主要GET失敗、最小書込み失敗、HTTPエラー多発 | **新規復旧DBへrestore** | 一般非公開。試験データ以外の書込みなし。新規復旧DBへ切り替えて旧アプリ起動。 |
| **5. アプリ再開前 (一般前)**| 実HTTPログイン失敗、セッション異常、復旧切替え締切到達 | **新規復旧DBへrestore** | 一般書込みなし。新規復旧DBへ切り替えて旧アプリ起動。 |
| **6. アプリ再開後 (一般後)**| **新規業務書込み発生後**の障害発覚、データ不整合 | **自動restore厳禁**<br/>**データ保全・責任者判断** | 1. 直ちにWebアプリを停止（ポート解放）<br/>2. 再開時刻以降の更新行・監査ログから新規書込み範囲を特定<br/>3. 新規書込みデータを差分エクスポート保全<br/>4. 責任者がロールフォワード（データ補正）か再投入前提restoreかを判断 |

---

## 6. 停止時間見積もり (技術所要時間 vs 運用安全枠)

本システムにおける停止枠は、**技術制約による長時間停止ではなく、人手確認や万一のロールバック判断に備えた「運用上の安全枠」**です。

| 工程内訳 | リハーサル実測 | 本番実測想定 | 備考 |
|---|---:|---:|---|
| 1. Webアプリ停止 (プロセス終了・ポート解放確認) | - | 約5〜10秒 | PowerShellでプロセス停止・確認 |
| 2. DB残存接続確認 (`pg_stat_activity`) | - | 約5秒 | 外部接続0件確認 |
| 3. 直前backup取得 (`pg_dump`) | 0.382秒 | 約1〜3秒 |  |
| 4. backup catalog検証 (`pg_restore -l`) | 0.036秒 | 約1秒 | ヘッダー目次検証 |
| 5. 事前検証restore (別DB) | 1.267秒 | 約2秒 | 破損検知の実弾検証 |
| 6. 停止中本番DBのsource再検査 (C1) | 2.061秒 | 約3秒 | manifest / sequence / enum |
| 7. migration実行 (C3: DDL + revision) | 1.890秒 | 約3秒 | ACCESS EXCLUSIVEロック保持時間は約1.8秒 |
| 8. 移行後DB target検査 (C4) | 2.194秒 | 約3秒 | schema / 件数 / FK孤立 / 重複 |
| 9. Webアプリ起動 (新コード) & ポートlisten確認 | - | 約5秒 | `python backend/run.py` 起動 |
| 10. 実HTTPログイン・最小スモーク (localhost) | 0.396秒 | 約5〜10秒 | 読取り＋1件最小書込み疎通 |
| 11. エラーログ確認・再開完了 | - | 約5秒 | コンソールログ確認 |
| **技術最短時間 (ノータイム自動実行)** | **12.310秒** | **約1分 〜 1分30秒** | 技術的な処理時間の実態 |
| **運用上の安全枠 (標準)** | - | **15分** | **人手確認・判断を含む標準枠 (復旧締切: 8分)** |
| **運用上の安全枠 (初回)** | - | **30分** | **初回の慎重運用・予備バッファ (復旧締切: 15分)** |

---

## 7. 運用体制と承認点 (最小体制マトリクス)

小規模・単一Windows環境に合わせ、Gate 1〜5の役割は維持しつつ**同一人物による兼務を可能**とします。

### 7-1. 最低限必要な3役
本番作業のGO/NO-GO判定に必要なのは以下の**3役**です（必要に応じて兼務可能。例: 2名体制なら作業者1名＋判断者1名、1名運用なら全役兼務）。

1. **作業実施者**: マイグレーションコマンド、バックアップ、アプリ起動・停止を実行する担当者。
2. **GO判断者**: 作業開始、マイグレーション実行、公開再開を承認・判断する担当者。
3. **rollback判断者**: 異常発生時に作業中止・バックアップ復旧への切替えを判断する担当者。

### 7-2. 承認ゲートと兼務設定

| 承認ゲート | 判定内容 | 担当役割 (兼務可能) | 判定基準 |
|---|---|---|---|
| **Gate 1: 作業開始GO** | メンテナンス突入・アプリ停止着手の可否 | GO判断者 / 作業実施者 | 作業手順確認済、バックアップ領域確保、新旧artifact照合済 |
| **Gate 2: migration実行GO** | DB変更の不可逆着手可否 | GO判断者 / 作業実施者 | Web停止確認済、DB接続0、直前backup検証成功、source検査合格 |
| **Gate 3: 公開再開GO** | サービス再開可否 | GO判断者 / 作業実施者 | target検査合格、Web起動確認、実HTTPログイン成功、最小スモーク合格 |
| **Gate 4: 異常時rollback GO** | 移行中止・旧環境切戻しの可否 | rollback判断者 | NO-GO条件抵触、または復旧締切（15分）超過 |
| **Gate 5: 作業完了確認** | メンテナンス終了・クローズ確認 | GO判断者 / 作業実施者 | 再開後15〜30分の安定稼働確認、バックアップ保全完了 |

---

## 8. 本番スモーク最小構成手順

> [!TIP]
> 専用検証DBにおいて既に18項目（業務シナリオ）＋24項目（並行/異常系）の網羅的試験は完了しています。
> 本番公開前スモークは、**「migration後に新コードが正常に読み書きできること」**を確認できる最小構成に絞り込み、本番データへの過剰な変更を避けます。

### 8-1. 最小構成スモーク内容

```powershell
# 1. 実ログイン (CookieおよびCSRFトークン取得)
$Session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$LoginBody = @{
    email = "admin@example.com"
    password = "$AdminPassword"
    user_type = "staff"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/auth/login" `
    -Method Post -Body $LoginBody -ContentType "application/json" -WebSession $Session

# 2. セッション整合性確認 (GET /api/auth/me) -> 200 OK
Invoke-RestMethod -Uri "http://localhost:5000/api/auth/me" -Method Get -WebSession $Session

# 3. 読取り疎通確認 (GET系主要3エンドポイント) -> 各200 OK
Invoke-RestMethod -Uri "http://localhost:5000/api/users" -Method Get -WebSession $Session
Invoke-RestMethod -Uri "http://localhost:5000/api/records" -Method Get -WebSession $Session
Invoke-RestMethod -Uri "http://localhost:5000/api/job-retention/users" -Method Get -WebSession $Session

# 4. 最小書込み疎通確認 (専用テスト利用者に対する支援記録1件の登録) -> 201 Created
$RecordBody = @{
    user_id = $TestUserId
    supporter_id = $SupporterId
    log_date = (Get-Date -Format "yyyy-MM-dd")
    support_record_type = "DIRECT_SUPPORT"
    support_content = "[TEST_SMOKE] Migration verification smoke record"
} | ConvertTo-Json

$RecordRes = Invoke-RestMethod -Uri "http://localhost:5000/api/records" `
    -Method Post -Body $RecordBody -ContentType "application/json" -WebSession $Session
```

### 8-2. 本番スモーク用データの扱いルール
- **テスト用識別子の明示**: 書込みデータには必ず `[TEST_SMOKE]` の接頭辞を付与し、本番業務データと即座に区別できるようにします。
- **スモークデータの事後処理**:
  - `SupportRecord` モデルには Soft Delete や `delete_reason` カラムは存在せず、削除APIも未実装です。
  - 新たな削除機能の追加実装は行わず、**専用テスト利用者 (`TEST_USER_xxx`) の枠組み内で `[TEST_SMOKE]` を明示した検証記録としてそのまま安全に保持**します。
  - 実在の利用者のデータには一切書き込みを行いません。

---

## 9. 実運用停止・移行・再開手順 (Step-by-Step)

### 【フェーズA: 停止・排出・事前確認】

#### 工程 1: 作業開始前確認 (Gate 1 承認)
- **操作**: 手順確認、ディスク容量確認 (DBデータサイズの3倍以上)、環境変数設定。
- **担当**: 作業実施者 / GO判断者（兼務可）
- **正常条件**: 全項目確定、ディスク容量十分、リハーサル合格記録確認。
- **証跡**: Pre-flightチェック記録。

#### 工程 2: Webアプリ停止 & ポート解放確認
- **操作**: 
  1. 稼働中のFlask Webアプリプロセスを停止 (Ctrl+C または `Stop-Process`)。
  2. ポート5000がListenしていないことを確認。
     ```powershell
     Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
     ```
- **担当**: 作業実施者
- **正常条件**: 出力が空（ポート5000が完全に解放されていること）。
- **証跡**: ポート確認コマンド出力ログ。

#### 工程 3: DB残存接続確認
- **操作**: PostgreSQLに対して以下のクエリを実行。
  ```sql
  SELECT pid, usename, client_addr, application_name, state, query
  FROM pg_stat_activity
  WHERE datname = 'ramp_db' AND pid <> pg_backend_pid();
  ```
- **担当**: 作業実施者
- **正常条件**: マイグレーション作業セッション以外の接続が **0件**。
- **証跡**: `pg_stat_activity` 照会結果ログ。

---

### 【フェーズB: バックアップ・検査・Migration】
※ 本フェーズは新コードartifact（`codex/slice2-release-rehearsal` ブランチの作業ディレクトリ）上で実行します。

#### 工程 4: 直前backup取得
- **操作**: 
  ```powershell
  pg_dump --format=custom --file "$ReleaseBackupFile" --dbname "$DATABASE_URL"
  ```
- **担当**: 作業実施者
- **正常条件**: exit code 0、ファイルサイズ > 0、SHA-256ハッシュ生成。
- **証跡**: バックアップファイル属性、SHA-256ハッシュログ。

#### 工程 5: backup検証 (Catalog & 別DB実restore)
- **操作**: 
  ```powershell
  # 1. catalog確認
  pg_restore --list "$ReleaseBackupFile" > "$ReleaseBackupCatalog"

  # 2. 一時検証DBへの実restore
  createdb --template=template0 "$ReleaseVerifyDb"
  pg_restore --no-owner --no-privileges --exit-on-error --single-transaction `
      --dbname "$ReleaseVerifyDb" "$ReleaseBackupFile"

  # 3. 検証DBに対するC1検査
  python -B backend/tests/check_slice2_release.py --env-file "$VerifyEnvFile" --mode source
  ```
- **担当**: 作業実施者
- **正常条件**: catalog正常、restore exit 0、C1検査 `passed: true`。
- **証跡**: catalogファイル、検証DB restoreログ、C1検査JSON。

#### 工程 6: 停止中本番DBのsource manifest検査
- **操作**: 
  ```powershell
  python -B backend/tests/check_slice2_release.py --env-file "$ReleaseEnvFile" --mode source
  ```
- **担当**: 作業実施者
- **正常条件**: exit 0、`passed: true`、revision=`f8e31a7c49b2`。
- **証跡**: C1実行ログ、JSON出力。

#### 工程 7: migration実行 (Gate 2 承認後)
- **操作**: Gate 2 承認後、セッションタイムアウトを明示して実行。
  ```powershell
  # lock_timeout=10s, statement_timeout=120s
  python -m flask --app backend.run db upgrade --directory backend/migrations/slice2_compat head
  python -m flask --app backend.run db upgrade --directory backend/migrations head
  ```
- **担当**: 作業実施者 / GO判断者
- **正常条件**: 双方exit 0で終了。全DDLが同一TX内でコミット完了。
- **証跡**: Flask-Migrate実行ログ。

#### 工程 8: 移行後DB target検査 & ロック残存確認
- **操作**: 
  ```powershell
  # 1. targetスキーマ検査 (C4)
  python -B backend/tests/check_slice2_release.py --env-file "$ReleaseEnvFile" --mode target

  # 2. ロック残存確認
  # SQL: SELECT count(*) FROM pg_locks WHERE mode = 'AccessExclusiveLock'; -> 0件
  ```
- **担当**: 作業実施者
- **正常条件**: C4 exit 0、`passed: true`、revision=`c731retentioncore`、ACCESS EXCLUSIVEロック残存0。
- **証跡**: C4出力JSON、pg_locksクエリ結果。

---

### 【フェーズC: 再開・実HTTP検証・完了】

#### 工程 9: Webアプリ起動 & ポートListen確認
- **操作**: 
  1. 新コードにてWebアプリを起動 (`python backend/run.py`)。
  2. ポート5000が正常にListenしたことを確認。
     ```powershell
     Get-NetTCPConnection -LocalPort 5000 -State Listen
     ```
- **担当**: 作業実施者
- **正常条件**: ポート5000がListen状態、コンソールにエラー出力なし。
- **証跡**: Webアプリ起動ログ、ポートListen確認ログ。

#### 工程 10: 最小スモーク実施 & 再開完了 (Gate 3 承認)
- **操作**: 第8節の手順に従い、実ログイン、GET系疎通（3件）、専用テスト利用者への最小書込み（1件）を実行。
- **担当**: 作業実施者 / GO判断者（兼務可）
- **正常条件**: 全リクエストが正常ステータス（200/201）を返却、`[TEST_SMOKE]` レコードの保持確認。Gate 3 承認。
- **証跡**: HTTPスモークログ。

#### 工程 11: 異常時バックアップ復旧手順 (Rollback Procedure)
- **前提**: 一般利用再開前、または新規書込みが発生していないことが確認された場合のみ実施する。
- **操作**: 
  1. Webアプリを停止（ポート解放）。
  2. 新規の復旧用DBを作成し、直前backupをrestore。
     ```powershell
     createdb --template=template0 "$ReleaseRecoveryDb"
     pg_restore --no-owner --no-privileges --exit-on-error --single-transaction `
         --dbname "$ReleaseRecoveryDb" "$ReleaseBackupFile"

     # アプリ接続ユーザーへの権限付与
     psql -d "$ReleaseRecoveryDb" -c "ALTER SCHEMA public OWNER TO $DB_USER; GRANT ALL ON ALL TABLES IN SCHEMA public TO $DB_USER; GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;"
     ```
  3. 復旧DBに対するC1検査 (revision=`f8e31a7c49b2`, `passed: true` を確認)。
  4. 旧アプリartifact (commit `6d8b343`) に切り替え、接続先を `$ReleaseRecoveryDb` に設定して起動。
  5. 旧環境でのGETスモークを実施し正常性を確認。
- **担当**: 作業実施者 / rollback判断者
- **正常条件**: 復旧DBへのrestore成功、C1合格、旧アプリ起動成功、主要API 200。
- **証跡**: restore実行ログ、復旧DB C1検査ログ、旧アプリ疎通ログ。

---

## 10. 本番実施可否の判定 (技術GO vs 運用GO)

### 【技術GO判定: 合格 (GO)】
- **判定結果**: **技術GO**
- **理由**:
  1. 専用DBを用いたデータ保持移行・リハーサルが完全に合格。
  2. source/targetスキーマ契約、enum、sequence、制約の完全一致を検証済。
  3. 技術所要時間は約1分〜1分30秒（DDLおよび検査自体は約12秒）であり、技術的な停止時間は極めて短小。
  4. ローカルPostgreSQL 17.10とのバージョン、エンコーディング、ロケール等の完全合致を確認済。

### 【運用GO判定: 条件充足待ち (保留)】
- **判定結果**: **運用条件確認待ち**
- **必要な確認事項**:
  1. **最低限3役の割り当て確認**: 作業実施者、GO判断者、rollback判断者の担当確認（兼務可・1〜2名で充足可能）。
  2. **作業枠の決定**: 運用安全枠（標準15分、または初回安全30分）と実施日時の最終決定。

上記2点の運用上の決定が行われ次第、本Runbookに従って直ちに作業を実施できます。
