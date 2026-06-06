# RAMP System アーキテクチャおよび実装規約

本ドキュメントは、RAMPシステムの堅牢性、保守性、およびセキュリティを担保するための**絶対遵守の設計・実装規約**です。AIエージェントおよび開発者は、実装時に必ずこの規約に従う必要があります。

---

## 1. 命名規則 (Naming Conventions)

**基本方針：業務概念を名前に残す。省略しない。**

- **良い例**: `User`, `Supporter`, `SupportPlan`, `MonitoringReport`, `CaseConferenceLog`, `DailyLog`, `BillingData`, `AuditLog`
- **避ける曖昧な単語**: `Data`, `Info`, `Record`, `Manager`, `Process`, `Handler`

### DBテーブル名
- `snake_case` の複数形
- 例: `support_plans`, `monitoring_reports`, `case_conference_logs`, `daily_logs`, `billing_data`, `audit_logs`

### Pythonクラス名
- `PascalCase`
- 例: `SupportPlanService`, `AuditLogService`

### Python関数名
- `動詞 + 対象`
- 例: `create_support_plan()`, `approve_support_plan()`, `activate_support_plan()`, `record_daily_log()`, `generate_billing_data()`

### フロントエンド
- Component名: `PascalCase` (例: `SupportPlanForm`)
- Hooks: `useXxx` (例: `useSupportPlan`)
- 型定義: `XxxType`, `XxxResponse`, `XxxPayload`

---

## 2. 権限ルール (Permission Rules)

権限は以下の5段階を基本とする。PII（個人特定可能情報）については厳格に別枠とする。
**絶対に `VIEW_PII` 権限のみで編集（更新・作成）を許可してはならない。**

### 基本権限
- `VIEW` (見る)
- `CREATE` (作る)
- `EDIT` (編集する)
- `APPROVE` (承認する)
- `DELETE` (削除する)

### PII専用権限
- `VIEW_PII` (見る)
- `EDIT_PII` (編集する)
- `EXPORT_PII` (出力する)

### ロール別初期値定義
- **支援員**: `VIEW` / `CREATE`
- **サビ管**: `VIEW` / `CREATE` / `EDIT` / `APPROVE`
- **管理者**: `VIEW` / `CREATE` / `EDIT` / `APPROVE` / `DELETE`
- **事務**: `VIEW` / `CREATE` / `EDIT` (billing系)
- **監査担当**: `VIEW` / `VIEW_AUDIT_LOG`

### 削除の原則
原則として物理削除は行わない。以下のカラムを用いて**論理削除**とする。
- `deleted_at`
- `deleted_by_id`
- `delete_reason`

---

## 3. API設計ルール (API Design Rules)

APIのエンドポイントは業務単位で切る。

- `/api/users`
- `/api/support-plans`
- `/api/monitoring-reports`
- `/api/case-conferences`
- `/api/daily-logs`
- `/api/billing-data`
- `/api/audit-logs`

### HTTPメソッドの使い分け
- `GET`: 取得
- `POST`: 作成
- `PATCH`: 部分更新
- `DELETE`: 論理削除

### 状態変更（業務イベント）の設計
状態変更は単なるデータ更新（PATCH）ではなく、業務イベントとして扱うため専用エンドポイントを用意する。

- **良い例**:
  - `POST /api/support-plans/{id}/approve`
  - `POST /api/support-plans/{id}/activate`
  - `POST /api/support-plans/{id}/revoke`
- **悪い例**:
  - `PATCH /api/support-plans/{id}` (body: `{ "status": "approved" }`)

---

## 4. Service層の責務 (Service Layer Responsibilities)

「API層は薄く、Service層を厚く」を徹底する。

### API層の責務
- リクエスト受け取り
- 認証ユーザーの取得
- 入力バリデーション
- Service層の呼び出し
- レスポンスの返却

### Service層の責務
- 業務ルールの適用 (例: `if plan.status == "approved":` などの判断)
- 権限チェック
- 状態遷移の管理
- データベースの更新
- 監査ログの記録
- 外部連携

---

## 5. エラーハンドリング規約 (Error Handling)

**`except: pass` は絶対禁止。**
エラーハンドリングは以下の定型フォーマットに従うこと。

```python
try:
    # 処理
    pass
except SpecificError as e:
    current_app.logger.exception(e)
    raise AppError("説明", status_code=400)
```

### 共通エラー分類
- `ValidationError`: 入力不正
- `PermissionDenied`: 権限なし
- `NotFoundError`: 対象なし
- `ConflictError`: 状態矛盾
- `BusinessRuleError`: 業務ルール違反
- `SystemError`: 想定外のエラー

### JSONレスポンス形式
エラー発生時は以下の構造でフロントエンドに返却する。
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "この操作を行う権限がありません。"
  }
}
```

---

## 6. 監査ログ規約 (Audit Log Rules)

監査ログは「誰が・いつ・何を・なぜ・どう変えたか」の事実を記録する。

### 必須項目
- `actor_supporter_id` (実行者)
- `action` (アクション名)
- `entity_type` (対象のモデル等)
- `entity_id` (対象のID)
- `before_value` (変更前値)
- `after_value` (変更後値)
- `reason` (理由)
- `ip_address` (IPアドレス)
- `user_agent` (ユーザーエージェント)
- `created_at` (記録日時)

### Action名の命名
大文字のスネークケースを使用する。
- 例: `CREATE_SUPPORT_PLAN`, `APPROVE_SUPPORT_PLAN`, `ACTIVATE_SUPPORT_PLAN`, `VIEW_PII`, `EDIT_PII`, `EXPORT_PII`, `CREATE_BILLING_DATA`, `OVERRIDE_AUDIT_WARNING`, `DELETE_DAILY_LOG`

### 監査ログと評価・リスクログの分離
- **監査ログ (`audit_logs`)**: 「事実」の記録
- **評価ログ (`risk_events`, `risk_counters`)**: リスク判定、未対応、アラート等の「評価」の記録。これらは監査ログとは明確にテーブルや概念を分離する。

---

## 初版の最重要ルールまとめ (The Golden 6 Rules)
1. 業務イベント（判断・状態遷移）はService層に置く。
2. 状態変更は専用APIエンドポイントにする。
3. PII権限は通常の権限と明確に分ける（VIEW_PIIとEDIT_PIIの分離）。
4. `except: pass` は使用禁止。
5. 監査ログは事実の記録とし、リスクログ（評価）とは分離する。
6. データの削除は原則として論理削除とする。
