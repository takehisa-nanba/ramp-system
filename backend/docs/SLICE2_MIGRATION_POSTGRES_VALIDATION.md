# 旧slice2データ保持移行検証（2026-10-01）

判定: **本番移行不可（NO-GO）**。旧slice2から現行mainへの移行経路が成立しない。移行失敗時のデータ保持と検証DBの隔離・削除は確認できたが、移行成功の検証ではない。

## 1. 実施方法

- PostgreSQL 17.10上で、開発DBリセット前に取得した旧slice2のcustom dumpをUUID付き専用DBへ復元した。
- 現行main反映済みコード（merge commit `5d5c5a5244f6388d115940d0bf4300709b44994f`）のAlembicを使い、`c731retentioncore`への通常upgradeを実行した。
- 通常upgrade失敗後、原因切り分けのため当該revisionのDDLのみを明示的トランザクション内で試し、必ずrollbackした。stampや履歴の書換えは行っていない。
- `backend/tests/validate_slice2_migration_postgres.py`で全publicテーブルの主キー・各列をメモリ内HMACで照合した。ID・状態・期間・関連先を含む既存値の比較結果のみ出力し、実際のレコード値・ID・HMAC鍵は保存しない。
- 列のNULL数、型・NOT NULL・enum定義、PK/FK/check/unique/index定義、FK孤立件数も比較した。対象はpublicスキーマ。シーケンス現在値・権限・所有者の一致は今回の判定対象外（restoreはno-owner/no-privileges）。
- dumpと集計JSONはリポジトリ外のアクセス制限済み領域に保存。接続URL・パスワード・個人情報はログや本報告に含めていない。
- 開発DBは読み取り専用スナップショット比較のみ。本番・開発DBへのmigrationは実行していない。専用DBはfinallyで削除し、pg_databaseに残っていないことを確認した。

再実行例（各パスは実環境のリポジトリ外パスへ置換）:

```text
python -B backend/tests/validate_slice2_migration_postgres.py --env-file <env-file> --dump <private-backup> --report <private-summary-json>
```

スクリプトの実行完了とmigration成功は別判定。集計JSONのmigration_successを確認すること。

## 2. migration前後比較

「後」はupgrade失敗後、および診断DDLのrollback後を指す。両方で差分はなかった。

| 項目 | 前 | 後 |
|---|---:|---:|
| Alembic revision | f8e31a7c49b2 | f8e31a7c49b2 |
| publicテーブル数 | 137 | 137 |
| 総行数（alembic_version含む） | 567 | 567 |
| users | 3 | 3 |
| supporters | 4 | 4 |
| support_plans | 5 | 5 |
| support_records | 7 | 7 |
| job_retention_contracts | 1 | 1 |
| job_retention_records | 0 | 0 |
| service_certificates / granted_services | 3 / 3 | 3 / 3 |
| audit_action_logs | 102 | 102 |
| FK孤立件数 | 0 | 0 |

主キーの追加・削除、既存列値の変更はいずれも0。列NULL数・スキーマ・enum定義も一致した。

- 計画: ACTIVE 4件、ARCHIVED 1件を維持。service config NULLは3件のまま。
- 契約: ACTIVE 1件を維持。service configは既存の非NULL値を保持。LEGACY_REVIEWへの変換は実行されていない。
- 契約service config列は旧slice2のNOT NULLのまま。SupportRecordのservice config列は未作成。
- 開発DBも127テーブル・339行、revision `c731retentioncore`のまま。全既存値・スキーマの比較差分0、FK孤立0。

## 3. 検出された差分

データ差分はない。一方、以下の移行阻害要因を検出した。

1. 旧revision `f8e31a7c49b2`は現行mainのAlembic履歴に存在せず、通常upgradeが失敗した。
2. Phase 1のDDLを直接試しても既存列と重複し、PostgreSQL SQLSTATE `42701`で失敗した。この診断処理はrollback済み。
3. Phase 1のsoft delete列・ACTIVE契約チェック制約・部分ユニークインデックス等は作成されていない。既存の旧slice2テーブル・インデックスはそのまま残った。

現行mainアプリの認証付きGET確認結果（移行失敗後の旧スキーマに対する結果）:

| API | HTTP |
|---|---:|
| /api/users | 200 |
| /api/records | 500 |
| /api/job-retention/users | 500 |
| /api/users/{id}/support-plans | 200 |
| /api/users/{id}/monitoring-reports | 200 |
| /api/users/{id}/case-conferences | 200 |

移行成功後のAPI正常性は未確認。200のAPIもこのGET範囲のみで、更新フローの保証ではない。

## 4. 想定内／想定外の判定

- 想定内: 移行失敗後に既存データ・状態・期間・参照先が保持され、開発DBへの影響がなく、専用DBを削除できた。
- 受入条件未達: 旧slice2からPhase 1へ通常migrationできず、追加スキーマの作成と主要APIの全正常応答を確認できない。
- 結論: 空DBへのmigration成功や別途実施済みの並行トランザクション試験から、旧slice2のデータ保持移行成功を推定してはいけない。

## 5. 本番migration判断の残件

1. 旧slice2の履歴・既存スキーマを入力とする、レビュー可能な移行経路を用意する。安易なstampや既存列の一括削除では解決しない。
2. 既にservice configを持つ契約と計画、旧slice2固有の履歴・関連テーブルをどう保持するか明文化する。既知のFKを一律NULLにしたり、既存ACTIVEを無条件に変換しない。
3. その移行を同じバックアップの専用DBに適用し、許可した差分だけが生じること、制約・インデックス・シーケンス・主要APIが正しいことを再検証する。
4. 移行後データを使った並行開始・終了と計画ACTIVE化の競合、および監査失敗時rollbackを再確認する。
5. 上記の完了とレビュー後に本番migrationを判断する。今回の結果では進めない。
