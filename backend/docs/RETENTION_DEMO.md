# Phase 2 開発環境への一本化

2026-10-03、ユーザーの明示承認により普段の開発DBへPhase 2を適用した。
既存レコードは削除・上書きせず、合成デモデータを追加した。

## 普段の起動

リポジトリrootのPowerShell:

```powershell
python -B -m flask --app backend.run run --host 127.0.0.1 --port 5000
```

別のPowerShell:

```powershell
cd frontend
npm run dev -- --host localhost --port 5173 --strictPort
```

入口は http://localhost:5173 。旧デモ用5178/5001は停止済み。
旧専用DBは未使用の状態で保持しており、自動削除しない。
旧デモ環境での操作履歴を移送したものではなく、開発DBへ初期デモデータを追加した。

## ログインと操作

職員コードは `demo-staff`。パスワードは旧デモ職員と同じ。
repository外の `%LOCALAPPDATA%\RAMP\retention-development\ログイン情報.txt` で確認する。
既存のログイン情報・職員権限は変更していない。

利用者ID 6「定着デモ利用者」、計画ID 7、サービス構成ID 3。
定着支援利用者一覧から支援計画を開く。
計画期間は2026-09-30〜2026-12-31、契約期間は2026-09-30〜2027-09-29。
個人情報・就職情報・受給者証・契約・DRAFT計画・支援項目を追加済み。
原案編集後、目標・課題・短期目標と会議を登録し、承認・同意・ACTIVE化へ進む。
評価はACTIVE化後に可能。期間・権限・状態のガードは解除していない。

## 適用・確認結果

- `scripts/unify_retention_development.py --apply-development` を一度実行。
- PostgreSQL custom形式backupを上記repository外フォルダーに保存。
- 保存先ACLは実行ユーザーとSYSTEMのみ。秘密情報・backupをGitへ保存しない。
- pg_restore --listによるarchive検査に成功。このbackupのrestore試験は未実施。
- revision: c731retentioncore → d842retentionplan。
- migration前後で全publicテーブルの既存行・既存列値をメモリ内比較し、一致。
- データ追加後も移行前の既存行・列値が保持されていることを確認。
- 5173の実HTTP経由で職員ログイン、利用者PII、定着一覧、計画履歴、詳細を確認。
- CSRF付きの計画詳細保存、version増分を確認。
- backendを5000で再起動。5173/5000のみ稼働。

setupは再実行しない。日常起動でmigration・初期化・データ削除は行わない。
