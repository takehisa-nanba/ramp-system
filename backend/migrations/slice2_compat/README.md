# 旧slice2専用の互換migration経路

対象は、検証済みの旧slice2実スキーマとAlembic revision `f8e31a7c49b2`を持つPostgreSQL DBのみ。
空DB、通常mainのDB、同じrevision名でも異なるスキーマには使用しない。

## 経路と通常mainへの復帰

```text
専用script directory: f8e31a7c49b2 -> c731retentioncore
通常script directory:              c731retentioncore -> 通常の将来のhead
```

通常mainの既存revisionを変更せず、別のscript directoryで旧DBから同じ到達点へのDDLを定義する。
両directoryを一つのversion_locationsに混ぜない。`c731retentioncore`は共通の到達点だが、
通常経路とこの経路の親・入力スキーマは異なる。

専用経路の`c731retentioncore_bridge.py`は実DDLを実行し、終了時のスキーマ契約を検証する。
成功した同一トランザクション内でAlembicがversionを進める。stampは使わない。
`f8e31a7c49b2_source.py`は既存DBの入口を認識するための定義であり、空DBから実行すると必ず失敗する。

## 再現可能な検証手順

リポジトリルートから次を実行する。env-fileは既存のsecret設定、dumpとreportはGit外のアクセス制限済み領域を指定する。

```text
python -B backend/tests/validate_slice2_bridge_postgres.py --env-file <env-file> --dump <private-custom-dump> --report <private-report-json>
```

このコマンドは既存DBの接続設定を使ってUUID付き専用DBを作り、dumpをそこだけに復元する。
アプリの接続先を明示的に専用DBへ固定し、次の2つのupgradeを実行する。

```python
with validation_app.app_context():
    upgrade(directory="backend/migrations/slice2_compat", revision="head")
    upgrade(directory="backend/migrations", revision="head")
```

検証ツールではdevelopment/source DBをread-onlyで比較する以外、migrationやデータ更新の対象にしない。
専用DBは成功・失敗ともfinallyで削除し、pg_databaseから消えたことを確認する。
CLIは検証失敗時に非0で終了する。DBエラーのSQL・パラメータ・レスポンス本文は出力しない。
通常のFlask CLIで専用directoryを指定する場合も、接続先を別途検証済みDBに固定する必要がある。
本番適用を許可する手順ではない。

## スキーマとデータの扱い

- `source_schema.json`は復元DBの全publicテーブルの列・型・NULL/default、enum、PK/FK/unique/check/indexの契約。データや資格情報は含まない。
- `target_schema.json`は変更対象テーブルの完全定義。これを固定したsource manifestに重ねたものが、mainに必要な共有スキーマと保持する旧slice2履歴拡張を合わせた到達形になる。変更対象外のテーブル・enumもsourceと完全一致を要求する。mainの空DBと物理的に同一ではなく、旧固有10テーブル・追加列・制約を意図的に残す。
- [差分一覧](../../docs/SLICE2_SCHEMA_DIFF.md)に再利用・変更・追加を記載した。既存列値を変更するUPDATEはない。
- 既存の契約ACTIVE、計画状態、FK、期間、署名・同意メタデータ、監査履歴は保持する。
- 旧同意ログ固有のdocument_version/action/signature_methodはNOT NULLだけ解除する。mainの新規書込みでは未知の旧メタデータはNULLとし、版や署名方式を推測しない。
- 旧固有テーブルは保存用。mainの新規処理はCoreのモデルを使う。旧固有レコードを別のCore台帳へ自動転記する処理はない。
- sequenceの値・定義・所有関係は変更しない。

## Fail Closedと運用条件

DDL前に全publicテーブルをACCESS EXCLUSIVEでロックし、検証と変更の間の書込みを防ぐ。
lock timeoutは10秒、statement timeoutは120秒。メンテナンス時間内にアプリの書込みを停止して使うこと。
この検証データ量に対する結果であり、大規模データでの所要時間を保証しない。

想定外のスキーマ・revision、未検証の制約・無効index、重複ACTIVE契約、日次ログ重複、
NULL sequence_no、旧定着記録の孤立がある場合は停止する。自動修復・一律NULL化・状態変換はしない。
終了時も全スキーマ契約を確認する。失敗したDDLとAlembic revision更新はtransactionでrollbackする。
不可逆な履歴削除を避けるためdowngradeは拒否する。復旧はレビュー済みbackup restore手順で行う。

今回のsource_schemaに一致しない別DBは、その差分とデータを追加レビューしてから別経路を設計する。
ガードを外したり、IF EXISTS/IF NOT EXISTSで回避してはいけない。
