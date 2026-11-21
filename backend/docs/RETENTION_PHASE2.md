# 就労定着支援計画 Phase 2

開発基準: main `8319e86`（Phase 1 `1cf766a` + 引継ぎ書）。
通常migrationの親revision: `c731retentioncore`。
参照様式: 添付 `book2.xlsx`「就労定着支援計画書　様式」A1:BJ54。
Excel本体・記入内容・秘密情報はリポジトリへ保存しない。

## 実装前調査と項目対応

実装前にチャットでモデル・API・承認・UI・migration・検証方針を報告した。
実コードには想定されていた `set_year_month` / `target_year_month` / 目標の
`achievement_status` は存在しない。前二者は既存目標の `target_period_start/end`
を使用し、達成度は既存 `GoalAssessment` を拡張する。

| 様式の項目 | 保存先・参照先 | 方針 |
|---|---|---|
| 作成日 | SupportPlan.draft_created_at / created_at | 重複しない |
| 計画詳細作成者 | JobRetentionPlanDetail.created_by_id → Supporter | 職員名はコピーしない。既存計画に作成職員FKはないため詳細作成者を記録 |
| 評価日・評価作成者 | detail.evaluation_date / evaluation_author_id → Supporter | 計画作成時NULL |
| 管理者・サービス管理責任者・就労支援員 | SupporterJobAssignment / Supporter / SupportPlan.sabikan_approved_by_id / User.primary_supporter_id | 職務・事業所・対象日で参照。担当が不明なら未確定のまま |
| 氏名・ふりがな・性別・生年月日・年齢・障害者手帳 | UserPII / masters | 既存PII権限で参照。年齢は帳票基準日から算出 |
| 支援区分 | ServiceCertificate.disability_support_classification | 計画のservice configと有効な証を参照 |
| 雇用事業主・業種・所在地・電話・担当者 | detail.job_placement_id → JobPlacementLog.employer → EmployerMaster | 詳細へコピーしない |
| 就職日・雇用形態 | JobPlacementLog.placement_date / employment_status | FKで保持。雇用形態は既存VARCHAR、正規・パート・契約／嘱託・派遣等を表現 |
| 就職前事業所からの引継ぎ事項 | detail.handover_notes | TEXT。事業所名専用の重複カラムは追加しない |
| 職場の物理的・人的環境 | detail.physical_work_environment / human_work_environment | 個別の自由記述 |
| 業務内容 | detail.job_description | 職種名と異なる具体的内容 |
| 賃金・休日・1日の勤務時間・休憩 | detail.contract_wage / holidays / daily_work_hours / break_time | 単位・交代勤務等を含む記述。既存の週労働時間を日労働時間として転用しない |
| 関係支援機関 | detail → retention_plan_organization_links → UserOrganizationLink → Organization | 本人の既存リンクを複数選択。名称・連絡先をコピーせず、CRMを新設しない |
| 健康状態 | detail.health_status_notes | 計画上の支援メモ。UserPII.disability_detailsをコピーしない。独立した診断・服薬モデルは現行コードにない |
| 生活環境・サポート体制 | detail.living_environment_notes | 家族氏名・連絡先は既存FamilyMember / EmergencyContact。こちらは支援体制の記述 |
| 利用目標・本人ニーズ | detail.user_needs | challengesやholistic policyと同一視しない |
| 長期・短期目標、設定日・達成予定日 | LongTermGoal / ShortTermGoal.description / target_period_start/end | 既存ツリー。新規目標モデルなし |
| 目標達成度 | GoalAssessment.achievement_status | LONG / SHORTの既存評価ログに追加。ACHIEVED / PARTIAL / NOT_ACHIEVED / NULL |
| 支援方針・内容、期間、頻度 | JobRetentionPlanSupportItem | 任意件数。3件固定にしない |
| 実施・達成・効果／満足度・残課題／対策 | SupportItemの評価項目 | 計画内容APIからは書換え不可。評価APIのみ |
| 特記事項・総括評価 | detail.special_notes / overall_evaluation | 特記事項は計画内容、総括は評価として分離 |
| 本人同意日・証跡 | DocumentConsentLog / SupportPlan.consented_at | 新規署名モデルなし |
| 説明者 | RECORD_PLAN_CONSENTのAuditActionLog.actor_supporter_id | DocumentConsentLog.idをentity_idとして同一transactionで記録。過去の不明値は推測しない |
| 事業所名・事業所番号・所在地・電話 | OfficeServiceConfiguration / OfficeSetting | 既存事業所設定から取得 |
| 紙の印・家族の押印・帳票セル位置 | 今回保持しない | 新たな紙署名モデル、PDF／Excel生成は対象外 |

## 追加スキーマ

- `job_retention_plan_details`: SupportPlan FK unique（0..1）、就職記録FK、作成職員FK、
  評価職員FK、版番号、上表の計画・評価フィールド、作成／更新日時。
- `job_retention_plan_support_items`: 詳細FK、順序、内容、期間、頻度、NULL許容の評価、
  論理削除日時／職員／理由。詳細＋順序のunique、正の順序、期間、評価区分check。
- `retention_plan_organization_links`: 詳細FK＋既存UserOrganizationLink FKの複合PK。
  参照の関連表のみ。関係機関そのものを新規保存しない。
- `goal_assessments.achievement_status`: NULL許容VARCHAR＋check。
  既存の評価本文・行は変更しない。

健康・生活メモは既存PII暗号処理を再利用。暗号処理が失敗してNULLになった場合は
新規フィールド専用型で例外にし、黙って保存しない。監査には平文を複製せず、
項目名・記録有無・変更フィールド・版番号を残す。
関係リンクの追加／解除も詳細監査へ記録する。支援項目の削除は論理削除のみ。
削除済み項目の順序番号は再利用しない。

## APIとServiceの境界

| Method | `/api/plans/{plan_id}` 以下 | 権限・内容 |
|---|---|---|
| GET | /retention-detail | VIEW。詳細なしはdetail=null、version=0。PIIはVIEW_PIIでのみ返し閲覧監査 |
| PUT | /retention-detail | 初回CREATE、以後EDIT。version必須。健康／生活の更新は別途EDIT_PII |
| POST | /retention-support-items | CREATE。任意件数を追加 |
| PUT | /retention-support-items/{item_id} | EDIT。対象plan/detail一致必須 |
| DELETE | /retention-support-items/{item_id} | DELETE＋10文字以上の理由。論理削除 |
| POST | /retention-evaluation | EDIT。ACTIVE時だけ評価を記録。評価者は認証職員から取得 |
| PUT | /retention-employment | EDIT。共通の就労元情報を明示的に更新 |

全APIはstaff認証、在職・有効職員、office一致、RETENTION config、利用者存在を検証。
tenant識別カラムは現行Coreにないため、Phase 1と同じoffice境界を使う。
他officeは同じ法人でも許可しない。

計画内容の更新はDRAFTだけ。契約期間を包含するACTIVEかつ未削除の契約が必要。
評価はACTIVE計画だけ。ARCHIVED、FINISHED契約後、PENDING系で計画内容を変更できない。
評価項目は初期NULLで、未実施・未達成を自動補完しない。
評価日は計画期間内かつJST本日以前。目標評価は既存GoalAssessmentへ履歴追加し、
最新の評価を表示する。未評価の選択もNULLで記録できる。
評価主体を選択しない場合は既存「支援員」を使用し、なければtransaction内で作成する。

更新は契約→計画の順で行ロックし、最新状態を読み直してから版番号を比較する。
同じ版からの2件目の更新は409。監査・詳細・項目・参照先変更は同一transactionで
commitし、監査失敗もrollbackする。finish / activateのPhase 1のロック順を維持する。
計画期間を縮小する既存APIも、支援項目が期間外へ出る変更を拒否する。

就労情報を二重保存しないため、企業情報更新は共通の参照先に反映する。
承認済み計画に参照される企業／就職記録、他利用者と共有する企業の変更はこのAPIでは拒否。
契約開始の根拠となった就職日はここでは変更しない。
詳細保存のemployment extensionで、企業情報と計画内容を一括transactionで更新できる。

## 承認・既存Coreへの影響

RETENTIONの承認前に、就職記録・企業名・就職日・本人ニーズ・業務内容・
長期目標／課題・各長期目標の短期目標・未削除の支援項目1件以上をServiceで確認する。
本人同席会議・サビ管・欠席時の既存条件を削除しない。
健康・職場環境・関係機関は任意。

SupportPlanのライフサイクル、契約状態、同意モデル、支援記録モデルは変更しない。
詳細がない既存ACTIVE/ARCHIVED計画は読める。承認済み計画へ後付けで内容を追加しない。
次期原案では新しい詳細を入力し直す（評価や署名済み内容を自動コピーしない）。
移行支援は新しい承認条件の対象外。
旧plan URLもRETENTIONの場合のみoffice／権限・編集状態をServiceへ委譲する。
既存approve APIでValidationErrorのimportが欠落していたため補い、入力不足を500にしない。

## UI

定着支援利用者一覧→サービス指定付きの既存支援計画サイクル。
サービスと対象計画を選択し、就労情報／職場・労働条件／本人・生活情報／支援内容／評価に分ける。
既存の目標・会議・承認・同意・activateの画面を継続使用する。
入力にはUXField、TextAreaWithCounter、共通UXSelectを使用。
未保存のサービス／計画／セクション切替えに確認を置く。
支援項目は1件ずつ保存し、別項目の未保存変更を巻き込まないよう編集を制御する。

## Migrationと検証方法

定着支援の改訂 `d842retentionplan` と職員・支援業務の改訂 `c620activitykey` を `e927merge` で統合する。
既存計画への一括詳細作成・状態変換・FK値変更なし。slice2_compatは変更しない。
データを失うdowngradeは自動実行せず停止する。

アプリ配置前には対象環境で通常migrationの適用が必要。
今回の検証はランダム名の専用DBのみ。既存開発DBには適用しない。

```powershell
python -B -m pytest backend/tests/test_retention_plan_phase2.py backend/tests/test_retention_core_phase1.py backend/tests/test_support_plan_service.py backend/tests/test_support_plan_transitions.py -q -o log_cli=false
python -B backend/tests/validate_retention_plan_postgres.py --env-file .env
python -B backend/tests/validate_retention_postgres.py --env-file .env
cd frontend
npm ci --no-audit --no-fund
npm run build
```

PostgreSQL検証スクリプトは通常Flask-Migrate/Alembicで空DB→head、
c731→headを実行。c731の合成既存データについて全既存テーブル・列値をメモリ内比較。
FK／unique／期間・区分check、監査失敗rollback、実ロック待ち＋競合409、
詳細→支援項目→approve→consent→activate→評価→支援記録→finishを確認する。
finallyで専用DBを削除し、pg_databaseに残っていないことを確認。
DB URL・パスワード・レコード本文・SQL例外パラメータを出力しない。

統合後の画面操作試験は `local_demo/smoke.py` で実施する。起動方法はルートの README.md を参照。

## 検証結果（2026-10-03）

- Phase 2の34件＋Phase 1／共通計画の68件、計102件成功。
- PostgreSQL 17.10で通常migrationの2経路、全既存列値保持、FK／unique／check、
  監査失敗rollback、実際の行ロック待ちと同一版の更新競合、主要更新APIフローを確認。
- Phase 1 PostgreSQLスクリプトも再実行し、同時start、finish先行／activate先行、
  partial unique競合、finish／activateの監査失敗rollbackを確認。
- フロントビルド成功。バンドルサイズの既存警告あり。
- Edge headlessで、詳細入力、PIIマスク、支援項目4件、未評価NULL、ACTIVE評価の操作成功。
  合成API応答を用いたコンポーネント検証であり、実ログインを通した全画面E2Eではない。
- 開発DB revisionは`c731retentioncore`のまま。専用DB残存0。
- 最終反復の1回で専用DBのDROPがProgrammingErrorとなった。後続の全検証は成功。
  残った1 DBは本作業固有の名前形式・所有role・開発DBとの相違を確認して削除し、
  残存0を再確認した。初回エラーのSQLSTATEは未採取で原因未確定。
  検証スクリプトの失敗出力にSQLSTATEと例外型を追加し、秘密情報を出さずに診断可能にした。

本番／開発DBへのmigration、mainへのmerge、pushはこの作業に含めていない。
使用開始にはレビュー後、通常migration `d842retentionplan` の適用が必要。
