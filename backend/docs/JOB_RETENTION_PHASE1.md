# 就労定着支援 Phase 1

## 調査と実装方針

対象は origin/main `590ad9e`。指定されたモデル、Service、Blueprint登録、設計・命名・UI規約を確認した。

- JobRetentionContract: 利用者と契約期間だけを持ち、事業所、状態、監査時刻、論理削除情報が欠けていた。既存テーブルを拡張した。
- JobRetentionRecord / PostTransitionFollowUp: 支援日、職員、内容を別々に保存していた。JobRetentionRecord は既存証拠の保持専用とし、新規実績は SupportRecord を使用する。旧データの自動複製はしない。
- SupportPlan: サービス識別がなく、同一利用者の計画が別サービスの計画を上書き・アーカイブする可能性があった。office_service_configuration_id を追加し、作成、連続性判定、有効化、複製で引き継ぐ。
- MonitoringReport は SupportPlan のFKを通じてサービスを識別する。CaseConferenceLog、AuditActionLog、UnresolvedRiskCounter も既存Coreを再利用し、専用の代替テーブルは作らない。
- ServiceCertificate / GrantedService / OfficeServiceConfiguration / ServiceTypeMaster には支給決定と指定確認に必要な情報が既にある。ダミー指定確認を撤去した。
- 6か月判定は暦月加算（対応日がない月は月末）を共通ドメイン関数で実施する。基準日のデフォルトは既存JST utilityを使用する。

## 業務API

すべて `/api/job-retention` 配下。職員JWT、通常権限と所属事業所をServiceで確認する。

- `GET /users`: 契約期間内のACTIVE契約利用者一覧。
- `GET /users/{user_id}`: アクセス可能な契約履歴。
- `GET /contracts/{id}`: 契約詳細。
- `POST /users/{user_id}/start`: `office_service_configuration_id`, `contract_start_date`, `contract_end_date`, `reason`。
- `POST /contracts/{id}/finish`: `contract_end_date`, `reason`。

開始にはCREATE、終了にはVIEWとEDIT、参照にはVIEWが必要。VIEW_PIIだけでは操作不可。Phase 1の範囲は職員の所属事業所内。開始日が未来の予約契約は扱わない。

開始時には在職、暦月6か月、ACTIVEかつ無効化されていない受給者証、非暫定RETENTION支給決定、事業所指定の期間を確認する。支給決定と指定は契約期間全体を満たす必要がある。不明な指定日・期限は拒否する。契約作成と監査を同時コミットし、例外時にはロールバックする。利用者行ロックと有効契約の部分ユニークインデックスで重複を防ぐ。

`POST /api/records` はサービス構成IDを指定すると認証済み職員として既存SupportRecordへ登録する。DIRECT_SUPPORTは0以上の秒数必須。計画を指定した場合、ACTIVEかつ支援日が計画期間内であることを必須とし、別利用者/サービスの計画も拒否する。`GET /api/records?office_service_configuration_id=...` はVIEWと事業所範囲を検証する。サービス未指定の旧フローは従来のサービス未指定記録を対象とする。

計画作成APIは `office_service_configuration_id` を受け取り、計画詳細・履歴にも同FKを返す。計画一覧の `active_plan` は同クエリ引数で選択できる。旧画面の未指定フローはNULLの従来計画を選択し、履歴も選択したサービス構成（未指定はNULL）で絞り込む。

## 画面

`/job-retention` に利用者一覧を追加。表示名（匿名表示名）、事業所、契約期間、利用状況と既存利用者詳細へのリンクを表示する。読込中、空状態、取得失敗・再試行を扱う。開始・終了の入力画面は今回の提示指示の対象外。

## データ移行

マイグレーション `c731retentioncore`（親 `b01649029bec`）をアプリ更新前に適用する。実DBへの適用はこの作業では行っていない。

旧契約の事業所を推測せず、FK=NULL、status=LEGACY_REVIEWで保持する。重複期間がある場合、新規開始は確認済みになるまで拒否する。旧契約の事業所を根拠資料から照合する作業は別途必要。新しい一覧で旧契約を利用中と表示することはない。既存のSupportPlan/SupportRecordもサービスを推測せずNULLのまま保持する。

削除API・物理削除処理は追加しない。旧記録へのdelete-orphan cascadeは除去した。履歴を破壊するdowngradeは拒否する。追加されるのは既存テーブルの列と制約のみ。

## 検証

- 暦月の境界、月末、うるう年、離職日
- 指定・支給決定・職員権限・事業所・削除利用者による開始拒否
- 二重開始、終了の再実行、監査失敗時のロールバック
- 認証、事業所間参照拒否、開始・終了API、共有SupportRecordへの保存
- 計画のサービス別履歴と有効化の分離
- SQLite旧スキーマへのマイグレーションとデータ保持
- 既存の計画承認・同意・モニタリング・就職登録テスト
- TypeScriptとVite本番ビルド

PostgreSQL実機での同時実行試験および本番データでの移行試験は未実施。

## レビュー指摘への修正

- 定着支援計画の作成・日付変更・次期原案複製は、SupportPlanServiceの共通ガードで同一利用者・サービスのACTIVE契約期間内に限定。検証前に日付を変更せず、APIの拒否時は付随する方針作成もロールバックする。
- 支援記録の計画指定はACTIVEおよび計画開始日・終了日（両端を含む）を検証する。計画への紐付け自体は従来通り任意。
- 計画履歴は有効計画と同じサービス構成で絞り込む。
- EmploymentServiceは未来の離職予定日を在職扱いとし、離職当日からNOT_EMPLOYEDとする。
- 上記の境界・拒否時の非保存を含む関連57テスト成功。支給決定・指定の契約全期間要件、ACTIVEの利用者単位ユニーク、旧フローのNULL許容は今回変更していない。

## 契約終了と計画有効化の整合性

RETENTION計画のACTIVE化でも、同一利用者・service configの未削除ACTIVE契約が計画の全期間を含むことを再検証する。契約行をロックし、契約終了処理との順序を確定する。開始日・終了日の一致は許可し、期間逸脱や終了・削除済み契約は拒否する。

契約終了では同一利用者・service configのACTIVE計画だけをARCHIVEDへ変更し、各計画の監査ログを契約終了と同時コミットする。署名済み計画のplan_start_date / plan_end_dateは変更しない。DRAFT/PENDING系は保持するが、終了済み契約ではACTIVE化できない。監査失敗時は契約・計画・監査すべてをロールバックする。

SQLiteによる境界・API・ロールバック試験を追加。PostgreSQL実機での並行トランザクション試験は未実施。
