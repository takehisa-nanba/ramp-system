# 旧slice2互換migration 検証結果（2026-10-02 JST）

結論: **同じ旧slice2バックアップからのデータ保持移行に成功**。許可した差分以外は0。
本番・開発DBにはmigrationを実行していない。本番適用は未実施。

## 1. 実施方法

main `5d5c5a5244f6388d115940d0bf4300709b44994f`のコードと履歴を確認し、旧slice2のcustom dumpを新規専用PostgreSQL 17.10 DBへ復元した。
[実装前スキーマ差分](SLICE2_SCHEMA_DIFF.md)を作成した上で、[専用互換経路](../migrations/slice2_compat/README.md)を実装した。

`f8e31a7c49b2 → c731retentioncore`は実DDLと全スキーマ事後検査を伴うAlembic migration。
その後、通常mainの`upgrade head`も成功し、revisionは`c731retentioncore`のままであることを確認した。
stamp、既存テーブル削除、既存列値UPDATEは行っていない。

[検証スクリプト](../tests/validate_slice2_bridge_postgres.py)は全publicテーブルの全既存列値と主キー集合をメモリ内HMACで比較する。
NULL数、FK孤立、enum、制約・index定義、sequenceの現在値/is_called・定義・所有関係も比較した。
レコードID・本文・個人情報・秘密情報はレポートに出力しない。

## 2. migration前後比較

以下は更新・競合試験用の合成データを追加する前の比較。

| 項目 | 前 | 後 |
|---|---:|---:|
| Alembic revision | f8e31a7c49b2 | c731retentioncore |
| publicテーブル数 | 137 | 137 |
| 総行数（revision行含む） | 567 | 567 |
| users | 3 | 3 |
| supporters | 4 | 4 |
| support_plans | 5 | 5 |
| support_records | 7 | 7 |
| job_retention_contracts | 1 | 1 |
| audit_action_logs | 102 | 102 |
| FK孤立 | 0 | 0 |

- revision行を除く全主キー集合と全既存列値が一致。既存NULL数・状態・期間・関連先も一致。
- 契約ACTIVE 1件を維持。計画ACTIVE 4件・ARCHIVED 1件を維持。
- 計画service config NULL 3件、非NULL 2件を保持。契約の非NULL service config 1件も保持。
- enum値・順序とsequenceの現在値/is_called・定義・所有関係は不変。
- 新規追加列はすべて既存行でNULL。対象外の列を推測で埋めていない。
- 旧固有10テーブルと追加列・既存履歴は保持。共有スキーマはmainの必要定義へ収束した。
- 合成データを追加した更新・並行実行試験の後にも、旧レコード全件の全既存列値が不変であることを再確認した。

## 3. 許可した差分と機能検証

許可したデータ差分はAlembic revision行のみ。許可したスキーマ差分は以下。

| 対象 | 変更 |
|---|---|
| job_retention_contracts | service configのNOT NULL解除、statusの新規行defaultをLEGACY_REVIEWへ変更、soft delete 3列・削除者FK・ACTIVEチェック・部分uniqueを追加 |
| support_records | service configとuser_daily_log_idのNULL列・FK・indexを追加 |
| job_retention_records | 既存contract_idへ不足していたFKを追加 |
| user_daily_logs | user_id + log_dateのuniqueを追加 |
| supporter_timecards | sequence_noをNOT NULLへ変更（NULLなら事前拒否） |
| staff_activity_allocation_logs | allocated_duration_secondsの新規行defaultを0に変更 |
| document_consent_logs | 旧固有3列のNOT NULL解除。既存値は維持 |
| 共有FK/index名 | 同義のFK 6件、index 1件をrename。再作成や既存FK値変更はなし |

全スキーマは固定した到達形のmanifestと一致。旧固有のstatus indexや認証check等は保持した。

主要GETはすべて200:

- `/api/users`
- `/api/records`
- `/api/job-retention/users`
- `/api/users/{id}/support-plans`
- `/api/users/{id}/monitoring-reports`
- `/api/users/{id}/case-conferences`

移行済みDBで18項目の更新API・結果検証に成功:
契約start、計画draft作成、期間外更新拒否、期間更新、目標更新、ケース会議作成、計画approve、
同意INSERT、activate、定着支援記録登録、期間外記録拒否、モニタリング作成・完了、
PENDING計画同意、finish、終了後activate拒否、ARCHIVED計画への記録拒否、署名済み終了日・PENDING保持。

別接続を使い、pg_blocking_pidsで実際の待機も確認した6シナリオ:

1. 同一利用者への同時start: 成功1件、ConflictError 1件。契約・開始監査とも1件。
2. finish先行 / activate後続: 終了成功、ACTIVE化は拒否、PENDING保持。
3. activate先行 / finish後続: 順に成功し、計画はARCHIVED。計画終了日は不変。
4. Serviceを迂回した同時INSERT: 部分uniqueにより片方がIntegrityError。
5. finish監査失敗: flush後も契約・計画・監査がrollback。
6. activate監査失敗: 旧ACTIVE計画と新PENDING計画・監査がrollback。

異常系9項目も成功:
未知の列、型変更、default変更、NULL制約変更、index欠落、revision不一致、
ACTIVE契約重複、旧定着記録の孤立を拒否。
さらにDDL途中に故障を注入し、Alembic経由で列・制約・データ・revision・sequenceの全rollbackを確認した。

既存Phase 1回帰テストは58件成功（SQLAlchemy Query.getの既存非推奨警告2件）。

## 4. 想定内／想定外の判定

許可したスキーマ変更とrevision更新のみ。想定外のデータ差分は0。
旧slice2固有のNOT NULL同意メタデータがmainの新規INSERTを阻害する点は、事前差分から明示的に対応した。
新しい同意に旧メタデータを捏造せず、NULLで未設定を表す。

バックアップファイルのSHA-256を実行前後にメモリ内で比較し、不変を確認。
開発DBは読み取り専用比較で全値・スキーマ・sequence不変。専用DBは削除後、pg_databaseで不存在を確認した。

## 5. 本番migration判断の残件

- 互換migrationと保持する旧拡張スキーマのレビュー。到達形は「main共有スキーマ＋旧履歴拡張」であり、空main DBと完全同一ではない。
- 本番候補の最新バックアップでもsource manifestに一致することを確認する。差異があれば停止して追加レビューする。
- 実データ量でのロック時間・メンテナンス時間とbackup restore手順を確認する。
- 旧固有テーブルの履歴を画面や帳票から参照する要件は別途整理する。今回、Coreへの自動転記・意味の再解釈は行っていない。
- 支給決定・指定の全期間要件やURAC更新管理は、以前からの業務判断として残る。

同じ検証バックアップに対する技術検証は合格。本番適用の承認や実行を意味しない。
