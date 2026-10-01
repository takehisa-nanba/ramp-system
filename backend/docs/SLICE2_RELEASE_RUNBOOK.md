# 旧slice2互換migration 本番作業runbook

この文書は将来の承認済み作業用。今回、本番・開発DBへのmigrationは実行していない。
リハーサル結果は[実測報告](SLICE2_RELEASE_REHEARSAL.md)を参照。

対象は承認済みsource manifestに一致する `f8e31a7c49b2` のPostgreSQL DB。
到達形は `c731retentioncore` の共有スキーマ＋旧履歴拡張。通常mainの空DBとは区別する。
本番のプロセス管理方式・停止/再開操作・許容停止時間は未確定。以下の作業票を埋めてレビューするまで実行不可。

## 作業票とsecretの扱い

- 承認された開始時刻、許容停止時間、復旧に切り替える締切、責任者、GO判定者。
- 適用するrelease commit/artifact、互換migration commit `94ab9ce`、復旧する旧アプリartifact。
  今回の旧アプリ疎通はローカルcheckout `6d8b343`で検証。本番の配置済みartifactと同一か別途照合する。
- 対象DBと環境、API・worker・scheduler・外部連携の停止/起動操作、バックアップ保管先、復旧先の新規DB名。
- 対象環境の保護されたenvファイルとPostgreSQL接続設定を準備する。`DATABASE_URL`、PG*設定、Flaskが読み込むenvの指す先が同じであることを保護された画面内で照合する。
- パスワードはコマンド引数へ書かない。接続設定はsecret管理またはアクセス制限したPGPASSFILE/サービス設定を利用する。
- dump、catalog、比較サマリ、作業ログはGit外・アクセス制限済み領域に置く。HTTPレスポンス本文、個人情報、URL、DB例外のSQL/パラメータはログに残さない。
- 以下の `$ReleaseEnvFile` / `$ReleaseBackupFile` / `$ReleaseVerifyDb` / `$ReleaseRecoveryDb` は保護された作業セッションで設定済みの値を表す。実値はこの文書に記載しない。
- バックアップ復旧は別DBを用意して切り替える。障害DBの一括削除、stamp、ガードの変更、場当たり的なデータ修正は禁止。

## 1〜14. 実行順序

各コマンドはリポジトリルートで実行し、終了コード0を確認してから次へ進む。異常時は連続実行しない。

| 工程 | 実行コマンドまたは操作 | 正常判定・次へ進む条件 | 異常時の処理 |
|---|---|---|---|
| 1. 作業開始前確認 | 作業票、release/復旧artifact、接続先、権限、ディスク容量、最新候補backupのリハーサル合格、残り時間を照合 | 全項目確定。DB所有者相当のDDL権限、backup読取り、検証/復旧DB作成権限がある | 未確定が1件でもあれば開始しない |
| 2. アプリ書込み停止 | 確定した操作でAPIへの流入、worker、scheduler、外部書込みを停止。処理中リクエスト・DB transactionを排出 | アプリ側の停止確認とDB側のセッション確認が一致。新規書込みが来ない | 停止不完全ならmigrationしない。無関係なセッションを自動killしない |
| 3. backup取得 | `pg_dump --format=custom --file "$ReleaseBackupFile"`。直前の読取り検査C1で主要件数を保護されたサマリに記録。ファイルSHA-256も保護領域へ記録 | exit 0、ファイル存在、容量>0、取得時点とrevision記録、既存backupを上書きしていない | backup失敗なら中止。DB未変更を確認して旧アプリ再開判断 |
| 4. backup検証 | `pg_restore --list "$ReleaseBackupFile"` の出力を保護領域へ保存。新規検証DBへC2でrestoreし、C1を実行 | catalog読取可、実restore成功、source一致、件数・既存値・sequenceが元DBと一致。全値比較は完全検証手順を使用 | 一つでも失敗なら本番DBを変更せず中止 |
| 5. source manifest検査 | 停止中の対象DBへC1を再実行。検証DBだけの検査で代用しない | revision=f8e31a7c49b2、manifest一致、enum一致、データ前提違反・sequence異常0 | 差分対象を調査。manifestを書換えたりIF EXISTSで回避しない |
| 6. migration実行 | C3で専用経路を実行 | exit 0。全DDL・事後スキーマ検査・revision更新が同一transactionで完了 | エラー/timeoutで中止。再実行せず、revision・rollback確認後に工程14へ |
| 7. revision確認 | C4のtarget検査、および通常mainの `upgrade head`（C3後半） | revision=c731retentioncore、通常mainから認識可能、想定していない将来revisionがない | 不一致ならアプリを再開しない |
| 8. DBスモークテスト | C4の主要件数を工程3と比較。FK孤立、ACTIVE重複、日次重複、sequence、target schemaを検査 | 件数一致、違反0、予定した差分だけ。audit件数も業務試験前は不変 | 一つでも想定外なら工程14へ |
| 9. APIスモークテスト | 新releaseをメンテナンス中の管理者限定経路で起動し、下記GETと専用試験利用者の1業務サイクルを実施 | HTTP成功、期間・状態・監査が正しい。実利用者は試験更新しない | エラーがあれば公開再開せず工程14へ |
| 10. アプリ再開 | 承認された順序でAPI公開、worker、scheduler、外部連携を再開 | 各プロセスhealth正常。migration時のACCESS EXCLUSIVEが残っていない | 再開を止める。書込み発生有無を記録し復旧方針を判断 |
| 11. 再開後確認 | 実際の入口からGET、ログイン/権限、代表画面、エラー率、DB待機・接続数、ジョブ稼働を確認 | 事前に決めた監視時間内で異常なし | 必要なら再停止。再開後の新規書込みを保全してから復旧判断 |
| 12. GO判定 | 責任者が全工程・実測時間・残件をレビューし作業票を完了 | NO-GO条件なし、許容停止時間内、検証ログとbackup保管を確認 | 条件付きのままGOと記録しない |
| 13. 異常時の中止条件 | 下記NO-GO一覧を常時適用。復旧締切を過ぎる前に判断 | 正常化が承認手順内で確認できる場合だけ継続 | 設定/データの即席修正で続行しない |
| 14. backup restore | API等を停止したまま新規復旧DBへC2を実行。旧revision・全値/制約/sequence一致を確認。旧アプリartifact＋復旧DB接続へ切替え、旧APIを確認して再開 | restore exit 0、revision=f8e31a7c49b2、比較一致、旧アプリAPI正常。責任者承認 | restore/旧APIに異常なら停止を維持してエスカレーション。障害DB/backupを破壊しない |

ACCESS EXCLUSIVEはSELECTもブロックする。単にPOST/PUTだけを遮断してGETを流し続ける運用にはしない。
特に既存の長時間SELECTやidle in transactionを事前に排出する。

### C1: source検査（読取り専用）

```powershell
python -B backend/tests/check_slice2_release.py --env-file "$ReleaseEnvFile" --mode source
```

exit 0と`passed: true`を両方確認。集計結果のみを保護領域に記録する。
現在のsource manifestにはsequence定義そのものは含まれない。補助検査で所有先、増分、cycle、次値の衝突/上限を検査し、backup restoreとの全sequence比較で保存を確認する。manifestがsequenceまで完全定義していると誤記しない。

### C2: 新規DBへのrestore

```powershell
createdb --template=template0 "$ReleaseVerifyDb"
pg_restore --no-owner --no-privileges --exit-on-error --single-transaction --dbname "$ReleaseVerifyDb" "$ReleaseBackupFile"
```

復旧時は新規の `$ReleaseRecoveryDb` を使う。既存DB名を再利用しない。
対象クラスタのencoding/localeと必要extensionを事前に確認する。
今回のrestoreは作成者所有でACLを復元しない方式。実運用のアプリ接続roleに必要な所有者/権限を与える手順も作業票で確定する。
CLIの終了だけで復旧成功とせず、全値・schema・sequence比較と旧アプリ疎通を必須とする。

### C3: migration（将来の承認済み作業のみ）

```powershell
python -m flask --app backend.run db upgrade --directory backend/migrations/slice2_compat head
python -m flask --app backend.run db upgrade --directory backend/migrations head
```

最初のコマンドが成功するまで2つ目を実行しない。実行するreleaseの通常headがc731retentioncoreであることを事前確認する。
lock timeout=10秒、statement timeout=120秒。これらは工程全体の停止時間の上限ではない。
DBエラーが出たら、内容を公開ログへ転送せず保護された診断経路で確認する。

### C4: target検査（読取り専用）

```powershell
python -B backend/tests/check_slice2_release.py --env-file "$ReleaseEnvFile" --mode target
```

exit 0、revision=c731retentioncore、違反0を確認し、主要件数を事前結果と比較する。
シーケンスを検査のためにnextvalで進めない。

## スモークテストと完全検証

### 本番直後のスモーク

- DB: revision、主要6テーブル件数、全FK孤立、ACTIVE契約重複、日次ログ重複、sequence安全性、target schema。
- GET 6種類: `/api/users`、`/api/records`、`/api/job-retention/users`、利用者のsupport-plans / monitoring-reports / case-conferences。
- 書込みは事前承認した専用試験利用者だけで1サイクル: start → 計画作成・目標・本人同席会議・承認・同意 → activate → 支援記録1件 → finish。
  ARCHIVED遷移、署名済み計画期間保持、監査作成を確認する。実利用者の契約開始/同意を模擬しない。
- リハーサル用の自動スモークは1ダミー利用者・計画2件・支援記録1件で、拒否ケース等を含む18項目。シナリオは既存検証と同じ固定業務日を使うため、本番では実日付と承認済み試験データで実施する。
- 今回のAPI検証はFlask test_clientによる内部疎通。reverse proxy/TLS・ネットワーク・実ログイン画面・実サービス再起動の検証は別途必須。

### 完全検証（本番DBで実行しない）

```text
python -B backend/tests/rehearse_slice2_release.py --env-file <protected-env> --dump <candidate-custom-dump> --output-dir <new-private-directory> --legacy-code-root <old-release-checkout>
```

専用DBだけに全値比較、6並行/rollbackシナリオ、18更新API/結果検証、9異常系、別DBへの実restore、旧API疎通を実行する。
さらに従来の `validate_slice2_bridge_postgres.py` も独立した完全検証として利用できる。
完全検証のfault injectionや合成データ追加を本番接続先に向けない。

## GO / NO-GO

以下のどれか一つでも該当すればNO-GO:

- source manifest/enum/revision不一致、データ前提条件違反。
- backup取得、catalog確認、検証restoreまたは全値比較の失敗。
- migration途中エラー/timeout、revision不一致、想定外のデータ差分。
- FK孤立、ACTIVE契約重複、日次ログ重複、sequence異常、target制約/index不一致。
- 主要API異常、業務スモーク失敗、旧アプリでの復旧疎通未確認。
- restore手順未検証、旧release/接続role/停止再開操作が未確定。
- メンテナンス時間が許容範囲を超える、または許容範囲/復旧締切が未承認。

再開後に実業務の書込みが発生した場合、古いbackupへの切替えはその書込みを失う。
そこで機械的にrestoreへ進まず、新規書込みを保全した上で責任者が判断する。
今回のrestoreリハーサルは「書込み停止中、アプリ公開再開前」の復旧を検証したものである。
