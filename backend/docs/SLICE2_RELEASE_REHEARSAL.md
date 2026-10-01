# 本番適用前リハーサル結果（2026-10-02 JST）

**データ保持移行・復旧リハーサルは合格。本番実施GOは未承認（現時点NO-GO）。**
本番・開発DBにはmigrationを実行していない。許容停止時間はユーザー回答で「未決定」。

## 1. 使用したバックアップの時点

ユーザーが最新候補として指定した前回の `before.dump` を使用。
アーカイブヘッダーの取得時点は **2026-10-01 18:47:54**。取得ホストのtimezoneはTokyo Standard Time（JST）。
これは今回あらためて本番DBから取得したbackupではない。
候補を専用DBへ復元した後、その専用DBから移行直前backupを再取得し、取得・検証・復旧の工程も実演した。
原本のSHA-256は実行前後にメモリ内比較して不変。dump・資格情報・個人情報はGitと公開ログに含めていない。

## 2. source manifest一致結果

migrationを一度も実行していない復元DBで事前検査を実施し、全項目合格。

- revision `f8e31a7c49b2`、137 publicテーブル、567行。
- source manifestで定義された列・型・NULL/default、PK/FK/unique/check/index、enumは完全一致。差分対象なし。
- 未検証constraint・無効indexなし。ACTIVE契約重複0、日次ログ重複0、NULL打刻sequence_no 0、旧定着記録の孤立0、全FK孤立0。
- sequenceの所有先、増分、cycle、次値と既存最大値・上限を検査し、異常0。
- **現在のsource manifest自体にはsequence定義は含まれない。** sequenceの静的manifestとの一致を主張せず、安全性検査と移行/復旧前後の定義・値・is_called・所有関係の一致で確認した。manifestは一切変更していない。
- 全事前検査合格時だけmigrationへ進む。ガードを緩めたり、DBに合わせてmanifestを作り直していない。

## 3. restore所要時間

初回候補restoreは **1.241秒**。
移行直前に専用DBから取得した新backupも、別の検証DBへ実restore（1.267秒）し、全値・schema・sequence一致を確認してからmigrationを開始した。

## 4. migration所要時間

最終計測runの結果。Python perf_counterによるクライアント側計測であり、SQL送信・応答と検査処理を含む。
各行には内訳と全体が混在するため、合算しない。

| 工程 | 実測 |
|---|---:|
| 候補dump restore | 1.241秒 |
| 移行前backup取得 | 0.382秒 |
| backup catalog検証 | 0.036秒 |
| 新backupの事前検証restore | 1.267秒 |
| 事前検証restoreの全値snapshot | 1.593秒 |
| 停止中source再検査 | 2.061秒 |
| migration開始→commit後のupgrade復帰 | 1.890秒 |
| 通常main upgrade head（no-op） | 0.027秒 |
| 全DDL送信→応答の合計 | 0.072秒 |
| revision UPDATE応答時点（開始から） | 1.888秒 |
| 移行後DB検証合計（全値・target schema・違反検査） | 2.194秒 |
| 主要GET 6件 | 0.396秒 |
| 業務スモーク18項目 | 0.234秒 |
| backup開始→スモーク完了 | 12.310秒 |
| 完全検証24項目（追加の合成データ） | 0.602秒 |
| 復旧restore | 1.381秒 |
| 復旧全値snapshot | 1.671秒 |
| 復旧旧API起動・GET 6件 | 2.824秒 |
| 独立した異常系9項目 | 18.582秒 |
| 全工程（検証・故障注入・削除を含む） | 46.959秒 |

revision UPDATEはmigration開始から1.888秒で応答し、commitを経て1.890秒でupgradeが復帰。
DDL処理自体の合計は72.461 msで、残りの多くはschema検査・接続等。DBサーバーCPU時間を示す値ではない。

主要DDL単位の送信〜応答合計:

| 対象 | 文数 | 時間 |
|---|---:|---:|
| `absence_response_logs` | 1 | 0.124 ms |
| `document_consent_logs` | 3 | 0.441 ms |
| `ix_support_plans_office_service_config_id` | 1 | 0.146 ms |
| `ix_support_records_office_service_configuration_id` | 1 | 1.707 ms |
| `ix_support_records_user_daily_log_id` | 1 | 1.286 ms |
| `job_retention_contracts` | 8 | 49.858 ms |
| `job_retention_records` | 1 | 1.479 ms |
| `staff_activity_allocation_logs` | 4 | 0.603 ms |
| `support_plans` | 1 | 0.116 ms |
| `support_records` | 4 | 6.902 ms |
| `supporter_timecards` | 1 | 0.556 ms |
| `uq_retention_active_user` | 1 | 7.862 ms |
| `user_daily_logs` | 1 | 1.381 ms |

## 5. ロック時間

- 全publicテーブル137件について、別接続からpg_locksを観測し、事前ACCESS EXCLUSIVE取得を確認。
- 一括LOCK文の取得時間: **1.341 ms**。他のアプリ接続が競合していない状態での値。
- LOCK開始からcommit後のupgrade復帰まで: **1.830秒**。各テーブルの保持時間の保守的な上限として扱う（個別ロック取得/サーバー内部の解放時刻を直接計測した値ではない）。
- migration完了後、ACCESS EXCLUSIVE残存0を確認。

job_retention_contracts、support_records、support_plans、user_daily_logs、supporter_timecards、document_consent_logsも同じ一括LOCKで取得し、transaction終了まで保持された。
読取りもブロックするため、全API流入とworker/scheduler等を停止・排出する運用が必要。
ロック観測の計測処理自体にも僅かな時間がかかる。実トラフィックを流した状態の停止/排出は今回検証していない。

## 6. migration後検証結果

`c731retentioncore`へ到達し、通常mainのupgrade headも成功。
137テーブル・567行を保持。revision行以外の全既存主キー集合・全既存列値・NULL数・状態・期間・service config・監査102件が一致。
sequence定義/現在値/is_called/所有関係、enumも不変。target schema完全一致、孤立/重複/sequence異常0。

主要GET 6種類はすべて200。業務スモークは専用ダミー利用者1名、計画2件、支援記録1件の範囲で18項目に成功。
契約start、計画作成・目標・会議・承認・同意、activate、定着支援記録、monitoring、finish、終了後activate拒否、署名済み期間保持を含む。
完全検証では別の合成データで24項目（上記18＋並行/rollback 6）を実行し、旧レコード全件の既存列値が不変であることも再確認した。

疎通はFlask test_client。実HTTP入口、TLS、reverse proxy、実ログイン画面、実サービスmanagerの停止/起動時間は含まない。
業務シナリオは既存テストと同じ固定業務日を使っている。本番スモークは承認済み試験データと実日付で別途実施する。

## 7. restoreリハーサル結果

**移行済み専用DBを実際に破棄**し、別名の新規DBへ移行前backupをrestoreした。

- restore成功: 1.381秒。
- revisionは `f8e31a7c49b2` に復帰。
- 全137テーブルの件数、全既存列値・主キー集合、FK/constraint/index、enum、sequenceが移行前と完全一致。
- 旧slice2コード `6d8b343` を別プロセスで起動し、旧契約一覧を含むGET 6件がすべて200。
- 別途、旧状態に対する異常系9項目で、DDL途中故障時のschema/データ/revision/sequence rollbackも確認。
- 故障注入テストの時間を除いた復旧関連工程は約 **6.183秒**（restore・全値比較・旧API起動を含む）。実配置での接続先切替え・サービス再起動時間は含まない。
- 最後に検証/移行/復旧用の専用DBをすべて削除し、不存在を確認。開発DBはread-only比較で不変。

## 8. 本番runbook

[SLICE2_RELEASE_RUNBOOK.md](SLICE2_RELEASE_RUNBOOK.md)に14工程を記載。
各工程に操作/コマンド、正常判定、異常時処理、進行条件を定義した。
source/targetの読取り専用ゲートは `backend/tests/check_slice2_release.py`。
完全リハーサルは `backend/tests/rehearse_slice2_release.py` で再現できる。

## 9. GO / NO-GO条件

source不一致、backup失敗、migrationエラー、revision不一致、想定外データ差分、FK孤立、ACTIVE/日次重複、sequence異常、主要API異常、未検証restore、許容停止時間超過はいずれもNO-GO。
許容停止時間・復旧締切が未承認の場合もNO-GOとする。
今回、技術検査で違反はないが、許容停止時間は未決定である。

## 10. 本番適用時の想定メンテナンス時間

今回の「backup開始→実restoreでbackup検証→source再検査→migration→DB/APIスモーク」は **12.310秒**。
これに **実サービスの停止・処理排出、実HTTP検証、再起動、責任者判断、復旧余裕** を加える必要がある。
したがって本番の停止枠はまだ確定できない。約12秒で本番作業が終わるとは判断しない。

この値は137テーブル・567行の候補、ローカルPostgreSQL 17.10、競合負荷なしでの実測。
事前runではmigration約3.46秒の例もあり、cache/負荷等で変動する。
将来のデータ増加時や本番インフラで同じ時間を保証しない。全量比較のメモリ/時間もデータ量に応じて再検証する。

## 11. 未解決事項

1. 許容停止時間、復旧切替え締切、GO責任者の承認。
2. 本番のプロセス管理方式、API/worker/scheduler/外部連携の停止・再開手順と実測。
3. 本番reverse proxy/TLS/ネットワーク/ログインを含む実HTTPスモーク。
4. backup復旧時の本番所有者/role/権限、encoding/locale/extensionの照合。今回は同一クラスタでno-owner/no-privileges restoreを検証。
5. 本番で使用する旧release artifactが検証済み旧コードと一致するかの確認。
6. 再開後に新規書込みが発生した場合の保全と復旧判断。今回検証したのは公開再開前の復旧。
7. sequenceの静的manifestは未定義（安全性と移行/restoreでの保存性は確認済み）。

## 12. 本番移行可否の技術判定

**今回の候補に対するデータ保持移行・backup/restore・内部業務疎通は技術合格。**
ただし運用上の許容時間と実配置での停止/再開・外部経路の確認が未確定のため、**本番実施の最終判定は現時点NO-GO**。
本番適用は実行していない。
