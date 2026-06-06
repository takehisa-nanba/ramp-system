# RAMP Architecture Rules v1.0

## 目的

RAMPは単なる障害福祉記録システムではない。

RAMPは、
利用者
↓
個別支援計画
↓
支援実施
↓
振り返り
↓
ケース会議
↓
計画修正
↓
監査
↓
組織学習

を一つの流れとして管理する業務OSである。

本規約は、
* 支援の質
* 監査耐性
* 保守性
* AIエージェント開発
を両立するための開発原則を定める。

---

# Golden 6 Rules

## Rule 1
業務イベントはService層に置く
状態遷移や業務判断をAPIに書いてはならない。
例：
* 計画承認
* 計画有効化
* モニタリング完了
* 利用者論理削除
これらはService層が実行する。
API層は、
* 認証
* 入力検証
* Service呼び出し
のみを担当する。

---

## Rule 2
状態変更は専用APIにする
許可：
POST /support-plans/{id}/approve
POST /support-plans/{id}/activate

禁止：
PATCH /support-plans/{id}
{
"status":"approved"
}
状態遷移は業務イベントであり、単なる更新ではない。

---

## Rule 3
PIIは通常業務データと分離する
利用者の個人情報は専用モデルで管理する。
権限も分離する。
VIEW
CREATE
EDIT
APPROVE
DELETE
とは別に、
VIEW_PII
EDIT_PII
EXPORT_PII
を持つ。
VIEW_PIIは閲覧のみ。EDIT_PIIを含まない。

---

## Rule 4
except: pass を禁止する
すべての例外は、
* 記録する
* 意味を持つ例外へ変換する
こと。

許可：
try:
...
except ValidationError:
...
except Exception as e:
logger.exception(e)
raise SystemError(...)

禁止：
except:
pass

---

## Rule 5
監査ログと評価ログを分離する
監査ログは事実を記録する。
例：
* PII閲覧
* 計画承認
* 利用者削除

評価ログはリスクを記録する。
例：
* 計画未作成
* モニタリング未実施
* 記録欠落

監査ログは人を評価しない。
評価ログは人を断罪しない。

---

## Rule 6
削除は原則論理削除とする
物理削除は禁止。
最低限、
deleted_at
deleted_by_id
delete_reason
を保持する。
利用者データは履歴を失わない。

---

# 命名規則

## モデル
PascalCase
例：
User
SupportPlan
MonitoringReport
CaseConferenceLog
AuditActionLog
UnresolvedRiskCounter

---

## テーブル
snake_case
複数形
例：
users
support_plans
monitoring_reports
audit_action_logs
unresolved_risk_counters

---

## Service
業務単位で命名する。
例：
SupportPlanService
MonitoringService
ComplianceService
FinanceService

禁止：
Manager
Handler
Processor
のような曖昧名称。

---

## メソッド
動詞 + 対象
例：
create_support_plan()
approve_support_plan()
activate_support_plan()
record_daily_log()
check_support_consistency()

---

# 権限規約

基本権限
VIEW
CREATE
EDIT
APPROVE
DELETE

PII権限
VIEW_PII
EDIT_PII
EXPORT_PII

削除は論理削除のみ。
DELETE権限は物理削除を許可しない。

---

# API規約

リソース単位で設計する。
例：
/api/users
/api/support-plans
/api/monitoring-reports
/api/case-conferences
/api/daily-logs

状態遷移は専用エンドポイントを利用する。

---

# 監査ログ規約

監査ログは以下を保持する。
actor_supporter_id
action
entity_type
entity_id
before_value
after_value
reason
ip_address
user_agent
created_at

---

# MVP原則

MVPでは以下を優先する。
利用者管理
個別支援計画
日報
モニタリング
ケース会議
管理確認事項

請求処理はMVP対象外とする。
ただし、
支援実績整合性チェック
監査アラート
計画未作成検知
は対象とする。

---

# 設計哲学

RAMPは記録のために存在しない。
RAMPは支援の質を維持し、組織が学習し、利用者利益を守るために存在する。
すべての実装判断は、
「監査に通るか」
ではなく、
「利用者にとって価値があるか」
を起点とする。
