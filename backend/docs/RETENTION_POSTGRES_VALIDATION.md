# PostgreSQL 定着支援検証結果

実施日: 2026-10-01（JST）
対象コード: mainに統合済みのPhase 1（PR #5、レビュー済みhead 49c8a39）
DBサーバーバージョン: PostgreSQL 17.10

## 実施方法

開発用.envから接続設定をメモリ上で取得。同じサーバー上にランダム名の専用DBを新規作成し、全migrationを空DBからc731retentioncoreまで適用した。開発DBのテーブルには書き込んでいない。接続URL・パスワード・dumpはGit管理対象に含めない。

競合試験は独立したFlask app context / DB sessionを2スレッドで実行。一方のトランザクションを意図的に保持し、pg_blocking_pidsで他方のロック待ちを実測してから解放した。単に処理を同時起動するだけの試験ではない。

## 結果

| 項目 | 結果 |
|---|---|
| 空DBから全migration適用 | c731retentioncoreまで成功 |
| 同一利用者の同時start | 1件成功、他方ConflictError。契約・開始監査とも1件 |
| finish先行、activate後続 | finish成功後、activateはValidationError。契約FINISHED、計画PENDING_CONSENT |
| activate先行、finish後続 | 両方成功。最終状態は契約FINISHED、計画ARCHIVED。署名済み終了日は維持 |
| Serviceを迂回する同時INSERT | 部分UNIQUEインデックスで他方をIntegrityError。契約は1件 |
| finishの監査失敗 | flush済みの契約終了・計画ARCHIVEをrollback。契約・計画ACTIVE、元の期間・監査件数を維持 |
| activateの監査失敗 | flush済みの旧計画ARCHIVE・新計画ACTIVEをrollback。旧ACTIVE／新PENDING_CONSENT、署名済み終了日・監査件数を維持 |

7項目すべて成功。試験用DBはfinallyで削除し、検証終了後の同プレフィックスDB残数0件を確認した。

開発DBの確認結果: revision c731retentioncore、利用者3件・職員2件・計画3件・支援記録2件。再構築直後の件数と一致。

## 再実行

リポジトリのルートで以下を実行する（引数は設定ファイルのパスのみ）。

```powershell
python -B backend/tests/validate_retention_postgres.py --env-file <開発用.envのパス>
```

DB作成権限が必要。毎回、専用DBを新規作成し、終了時に削除する。シナリオ間のTRUNCATEは専用DBだけが対象。接続・例外の詳細は出力せず、成功項目または例外クラスのみ出力する。

## 範囲と残件

- 今回は開発DBをユーザー許可のもと再構築した後の検証。旧slice2データを保持した移行試験の成功を意味しない。
- 本番データ移行と本番デプロイは未実施。
- 支給決定・指定の全期間要件とURAC更新管理は業務判断として残る。
- 初期投入時に見つかったseed_admin.pyの旧is_scheduled/statusへの代入は、現行approval_statusへの代入に修正。修正後の初期投入と既存一覧APIの200応答は確認済み。
