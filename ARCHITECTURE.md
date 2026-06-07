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

## 1. 利用者ファースト
RAMPは記録のために存在しない。
RAMPは支援の質を維持し、組織が学習し、利用者利益を守るために存在する。
すべての実装判断は、「監査に通るか」ではなく、「利用者にとって価値があるか」を起点とする。

## 2. 骨格が先、支援サイクルは後
RAMPは単なる「支援サイクルを回すためのツール」ではなく、「福祉事業所という組織そのものを表現するシステム」である。

支援サイクル（利用者 ➔ 課題 ➔ 目標 ➔ 支援 ➔ 記録）は活動であり、活動は主体が存在して初めて成立する。したがって、まず定義されるべきは強固な「骨格」である：
- 法人 (Organization / Corporation)
- 事業所 (Office)
- 職員 (Staff)
- 職務・権限 (JobTitle / Role)
- 利用者 (User)

福祉実務は、「誰が」「どの立場で」「誰に対して」「何を行ったか」の関係性によって初めて成立する。
受給者証履歴、多層ロール、同一時間帯の重複登録防止、本人同席承認ガードレールなどの厳格なルールは、単なる「設定」や「機能」ではない。それは、このRAMP世界における「物理法則」であり、この骨格が正しく定義されて初めて、その上に生える器官である支援計画や日報、モニタリングが本当の意味を持つ。

## 3. 権限は「職員」ではなく「文脈と責務」に付与される
RAMPにおいて、権限は個人としての職員に静的に紐づくものではない。権限は「職務（JobTitle）」と「文脈（Context）」の交差点にのみ動的に付与される。

職員は複数の立場（システム管理者、特定の事業所の管理者、一般支援員など）を同時に持ち得るが、見える世界と実行可能な行動は、その時点で選択された「文脈（誰の、どの事業所の、何の立場として操作しているか）」によって決定される。
- 例：単に「サービス管理責任者（サビ管）の有資格者だから計画を承認できる」のではない。「**この事業所の、この利用者の担当サビ管として、今この文脈に立っている**」からこそ承認ボタンが押せる。

## 4. 支援サイクルを支える「責任の追跡可能性（Accountability）」
RAMPの真の中心は、単に支援サイクルをスムーズに回すことではない。その背後にある**「責務（Responsibility）」の連鎖**と、それを証明する**「責任の追跡可能性（Accountability）」**である。

計画の作成、ケース会議の開催、署名同意、日報の記録、モニタリング評価。これらすべての業務イベントは、単なるテキストデータの蓄積ではなく、「誰が、どの立場で、どのような意図で行ったか」という責務の証明書の連鎖（監査証跡）である。この責務の連鎖が盤石であるからこそ、将来のAIアシスタントや自動請求システム、そして行政監査に対しても、揺るぎない信頼性とコンプライアンスが担保される。
