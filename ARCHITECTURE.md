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

## Rule 0. RAMPは「入力効率化システム」にしてはならない
RAMPの目的は、単に事務作業の入力速度を上げたり、監査をやり過ごすための形骸化したフォーム管理ツールになることではない。過剰な効率化によって支援員の「思考の排除」や「記録の希薄化」を許せば、RAMPはその存在価値を失う。RAMPは、記録を通じた「責務の対話」「プロセスの観測」「組織の学習」を維持するために存在する。

## 1. 利用者利益を守る「介在」
すべての実装判断は、「監査に通るか」ではなく、「利用者にとって価値があるか」を起点とする。RAMPは代わりに考えたり判断したりする「介入」をせず、過去と現在、仮説と検証の間に「介在」することで、人間（支援員と利用者）の認知と判断を補助する。

## 2. 骨格が先、活動は後
福祉実務は、「誰が」「どの立場で」「誰に対して」「何を行ったか」の関係性によって初めて成立する。したがって、まず定義されるべきは強固な「骨格（関係の束）」である：
- `Staff ↔ Office` （所属と稼働時間）
- `Staff ↔ Role` （システム・組織上の権限と責任）
- `Role ↔ User` （担当サビ管と利用者の関係）
- `User ↔ Service` （契約と受給者証の適用関係）
受給者証履歴、多層ロール、同一時間重複防止などのルールは、機能ではなく、この骨格が従うべき「物理法則（社会契約）」である。

## 3. 権限は「職員」ではなく「文脈と責務」に付与される
権限は個人としての職員に静的に紐づくものではない。「職務（JobTitle）」と「文脈（Context：誰の、どの事業所の、何の立場として操作しているか）」の交差点にのみ動的に付与される。これにより、責任の所在（Accountability）を常に明確にする。

## 4. 状態ではなく「変遷（タイムライン）」と「意思決定（Decision）」を管理する
福祉支援とは一時的な状態（State）ではなく、時間の経過とともに刻々と変化するプロセス（Process）である。行政監査や信頼性の本質は、「今どうなっているか」ではなく、「なぜその意思決定（Decision）を経て今に至ったか」の証明にある。
- 例：計画のバージョン履歴、受給者証変遷、遅延・遡及理由の記録（10文字以上の入力制限）、本人不在の会議理由、論理削除理由の記録。
RAMPは、関係性の変遷とその裏側にある「意思決定の理由（Decision）」を時間の糸（タイムライン）として残し続ける。

## 5. 答えではなく「観測可能性（Observability）」を管理する
利用者理解や支援方針に、システムが提示できるような「唯一の絶対的な正解（答え）」は存在しない。あるのは、その時点で最も妥当な「仮説」だけである。
したがって、RAMPは代わりに考えたり答えを出したりせず、「後から人間が何度でも客観的に事実を見直せる観測可能性（Observability）」を最大化し、維持し続ける。この信頼性の高い観測結果の蓄積を通じてのみ、人間は「認知の更新（組織学習）」に到達できる。
