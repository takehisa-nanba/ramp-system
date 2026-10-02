# 就労定着支援システム Phase 1 完了・開発基準点一本化 引き継ぎ書

**作成日**: 2026年10月2日  
**対象リポジトリ**: `takehisa-nanba/ramp-system`  
**正式ブランチ**: `main`  
**正式コミット（HEAD）**: [`1cf766a`](file:///c:/Users/nanba/Desktop/ramp-system) (`feat(retention): integrate slice2 compat migration and rehearsal validation assets`)  
**DB基準リビジョン**: `c731retentioncore`  

---

## 1. 背景と意思決定の経緯

### 1-1. 旧slice2移行の中止
- 本環境は**本番運用前**のステージであり、初期開発段階の旧データ（`before.dump`）を本番移行する必要性がないと判断。
- 旧slice2互換マイグレーション（bridge migration）によるデータ救済・復旧作業はすべて**終了・中止**。
- `before.dump` の探索も終了。

### 1-2. 新基準への一本化
- **現行Phase 1コードベース**を唯一の正式な設計・実装基準として採用。
- 開発DB（`ramp_db`）は通常Alembicマイグレーションのみを用いて、空DBからクリーンに再構築完了。
- 分散していた2ブランチ（`feature/job-retention-slice2` および `codex/slice2-release-rehearsal`）の成果を精査し、最新の `main` へ一本化完了。

---

## 2. Git ブランチとコミット構成

### 2-1. ブランチ一覧と位置づけ

| ブランチ名 | コミット | 位置づけ・役割 |
| :--- | :--- | :--- |
| **`main`** | **`1cf766a`** | **正式な開発・運用の基準点（一本化完了）** |
| `feature/job-retention-slice2` | `3393961` | 旧slice2実装および確定版Runbook保全ブランチ（参照用・更新停止） |
| `codex/slice2-release-rehearsal` | `46bca10` | 互換migration・技術リハーサル検証成果ブランチ（mainマージ済み） |

### 2-2. 主要コミット履歴（main HEAD `1cf766a` への合流）
```text
*   1cf766a (HEAD -> main) feat(retention): integrate slice2 compat migration and rehearsal validation assets
|\  
| * 46bca10 docs: sync finalized slice2 release runbook
| * 3db874e fix(seed): align UserDailySchedule cancellation with model property and add validation docs
| * 08c5726 Add measured slice2 release and recovery rehearsal runbook
| * 94ab9ce Add explicit data-preserving slice2 compatibility migration
|/  
*   5d5c5a5 Merge pull request #5 from takehisa-nanba/feature/job-retention-core
|\  
| * 49c8a39 fix: synchronize retention contract finish and plan activation
| * 7da2007 fix: enforce retention plan periods and service history boundaries
| * 3ee1c67 feat: integrate job retention support into shared RAMP core
|/  
* 590ad9e feat(attendance): display planned and actual work sessions (#4)
```

- **履歴の保全**:
  - 旧slice2最終コード `6d8b343` は `feature/job-retention-slice2` の履歴として完全参照可能。
  - すべてマージコミット（`--no-ff`）により統合され、履歴消去・force push・resetは一切行っていません。
  - Working tree は完全に clean です。

---

## 3. データベース環境と再構築手順

### 3-1. DB基本構成
- **DBMS**: PostgreSQL 16 (Windows ローカルサービス)
- **対象DB**: `ramp_db`
- **所有者**: `ramp_user`
- **Alembic Revision**: `c731retentioncore (head)`
- **publicテーブル数**: 127
- **FK孤立**: 0件
- **シーケンス整合性**: 123シーケンスすべて整合（`pg_sequences` 検査合格）

### 3-2. 通常の環境構築手順（空DBからの構築）
今後の開発・検証でクリーンなDBが必要な場合は、以下の通常手順で構築します。
※ `backend/migrations/slice2_compat` は絶対に使用しないでください。

```powershell
# 1. 既存DBの破棄と空DBの作成
dropdb -U postgres -h 127.0.0.1 --if-exists ramp_db
createdb -U postgres -h 127.0.0.1 --template=template0 --owner=ramp_user ramp_db

# 2. 通常Alembicマイグレーションの適用 (c731retentioncore まで自動適用)
python -m flask --app backend.run db upgrade --directory backend/migrations head

# 3. 初期シードデータの投入
python backend/seed_admin.py
```

### 3-3. 現在の開発DB（`ramp_db`）の状態
現在稼働中の `ramp_db` は、通常マイグレーションおよび `seed_admin.py` 投入後、Phase 1 E2E基本フロー検証を通過した状態です。
- 管理者アカウント（`admin-001` / `admin@example.com`）に「管理者」および「サービス管理責任者」の職務アサインが存在。
- 検証用テスト利用者、受給者証、就職実績、定着支援契約、個別支援計画、支援記録が安全に保存されています。
- そのまま開発・動作確認用として使用可能です。

---

## 4. 旧slice2資産の取り扱い方針

1. **`backend/migrations/slice2_compat/`**
   - **用途**: 将来的に旧システムデータを救済・参照する必要が生じた場合の参考資産。
   - **運用ルール**: 通常のマイグレーションチェーン（`backend/migrations/`）からは完全に隔離されています。通常の `db upgrade` コマンドで本ディレクトリを指定・実行してはいけません。
2. **ドキュメント・Runbook類**
   - `backend/docs/SLICE2_RELEASE_RUNBOOK.md`
   - `backend/docs/SLICE2_RELEASE_REHEARSAL.md`
   - `backend/docs/SLICE2_BRIDGE_VALIDATION.md`
   - `backend/docs/SLICE2_MIGRATION_POSTGRES_VALIDATION.md`
   - これらはリハーサル成果および技術的決定ログとしてリポジトリ内に保持されています。現在の運用Runbookではなく、歴史的検証記録として扱います。

---

## 5. 実装済み仕様と検証結果

### 5-1. Phase 1 就労定着支援コア仕様

1. **契約管理 (`JobRetentionService`)**:
   - 就職日（`JobPlacementLog.placement_date`）から6ヶ月経過していない利用者の契約開始を fail-closed で遮断。
   - 有効な受給者証（`ServiceCertificate`）・支給決定（`GrantedService`）・事業所定着指定（`OfficeServiceConfiguration`）の厳格な検証。
   - 契約期間の重複禁止（部分一意インデックス / `with_for_update()` による同時実行排他制御）。
   - 契約終了（`finish`）時の監査ログ記録と、紐づく有効計画の自動アーカイブ。

2. **計画連携 (`SupportPlanService` / `SupportPlan`)**:
   - 計画期間が契約期間内に収まっていることのガードレール。
   - 承認（`approve`）条件:
     - 承認者がサービス管理責任者であること。
     - 長期目標・短期目標が設定され、課題（`challenges`）が入力されていること。
     - 本人同席の会議（`CaseConferenceLog` / `PERSON_CENTERED_MEETING`）が実施済みであること。
   - 同意（`consent`）: 電子同意ログ（`DocumentConsentLog`）の発行。
   - 有効化（`activate`）: サビ管による最終有効化処理。旧計画との整合性検証。

3. **支援記録 (`SupportRecordService` / `SupportRecord`)**:
   - 定着支援サービス設定（`office_service_configuration_id`）に紐づく訪問支援・定期面談記録の作成。
   - 権限（`VIEW`, `CREATE`）のテナント分離検証。

### 5-2. 自動テスト体系

| テストコマンド | 内容 | 結果 |
| :--- | :--- | :--- |
| `pytest backend/tests/test_retention_core_phase1.py` | 境界値、ライフサイクル、fail-closed、ロールバック検証 | **58 passed** |
| `python -B backend/tests/validate_retention_postgres.py --env-file .env` | PostgreSQL実機での使い捨てDB自動生成・並行競合・ロールバック検証 | **全18項目パス** (`DISPOSABLE_DATABASE_REMOVED`) |

### 5-3. アプリケーション疎通・E2Eフロー確認

`python backend/run.py` 起動下で以下の全ルートおよび基本業務サイクルが 200/201 で動作確認済み:

- `POST /api/auth/login` (管理者ログイン)
- `GET /api/users` (利用者一覧)
- `GET /api/records` (支援記録一覧)
- `GET /api/job-retention/users` (就労定着対象者一覧)
- `GET /api/users/<id>/support-plans` (個別支援計画一覧)
- `GET /api/users/<id>/case-conferences` (ケース会議一覧)
- `GET /api/users/<id>/monitoring-reports` (モニタリング一覧)
- **1サイクル更新フロー**:
  - `POST /api/job-retention/users/<id>/start` (`201 Created`)
  - `POST /api/plans/` (`201 Created`)
  - `PUT /api/plans/<id>/goals` (`200 OK`)
  - `POST /api/case-conferences` (`201 Created`)
  - `POST /api/plans/<id>/approve` (`200 OK`)
  - `POST /api/plans/<id>/consent` (`201 Created`)
  - `POST /api/plans/<id>/activate` (`200 OK`)
  - `POST /api/records` (`201 Created`)
  - `POST /api/job-retention/contracts/<id>/finish` (`200 OK`)

---

## 6. 次の開発者への注意事項・開発フロー

1. **ブランチ運用**:
   - 新機能の開発や修正は、必ず最新の `main` から feature ブランチを作成して着手してください。
   - `feature/job-retention-slice2` や `codex/slice2-release-rehearsal` からの派生は行わないでください。
2. **マイグレーション追加時**:
   - 新規マイグレーションは常に `backend/migrations/` に追加してください。
   - `python -m flask --app backend.run db migrate --directory backend/migrations -m "..."`
3. **シードデータの追加・修正時**:
   - `seed_admin.py` を修正する場合、モデルの属性・プロパティ（特に setter の有無）に留意してください。
4. **機密情報の管理**:
   - `.env` の接続URLや暗号化キー（`PII_ENCRYPTION_KEY`、`FERNET_ENCRYPTION_KEY`）をログやコミットへ直接出力・コミットしない運用を徹底してください。
