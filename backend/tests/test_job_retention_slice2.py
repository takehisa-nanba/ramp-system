# backend/tests/test_job_retention_slice2.py

import pytest
import datetime
import dateutil.relativedelta
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models import (
    JobRetentionContract, RetentionSupportPlan,
    calculate_plan_end_date, calculate_max_review_deadline,
    MonthlyRetentionReport
)
from backend.app.services.job_retention_service import JobRetentionService
from backend.tests.test_job_retention_auth import auth_setup, get_headers


# ====================================================================
# 1. 計画終了予定日計算 (6か月 - 1日) & 月末跨ぎ・うるう年の検証
# ====================================================================
def test_calculate_plan_end_date():
    """
    【仕様】原則 start_date + 6 calendar months - 1 day
    - 2026/09/01開始 -> 終了予定日: 2027/02/28 (平年2月末)
    - 2023/09/01開始 -> 終了予定日: 2024/02/29 (うるう年2月末)
    - 月末跨ぎの検証:
      - 2026/03/31開始 -> +6か月は9/30 -> -1日は 2026/09/29
      - 2026/08/31開始 -> +6か月は2027/02/28 -> -1日は 2027/02/27
      - 2026/01/31開始 -> +6か月は2026/07/31 -> -1日は 2026/07/30
    """
    # ユーザー指定例: 2026/09/01 -> 2027/02/28
    d1 = datetime.date(2026, 9, 1)
    assert calculate_plan_end_date(d1) == datetime.date(2027, 2, 28)

    # うるう年
    d_leap = datetime.date(2023, 9, 1)
    assert calculate_plan_end_date(d_leap) == datetime.date(2024, 2, 29)

    # 月末パターン 8/31 -> 2/27 (翌年2/28 - 1日)
    d_aug = datetime.date(2026, 8, 31)
    assert calculate_plan_end_date(d_aug) == datetime.date(2027, 2, 27)

    # 月末パターン 3/31 -> 9/29 (9/30 - 1日)
    d_mar = datetime.date(2026, 3, 31)
    assert calculate_plan_end_date(d_mar) == datetime.date(2026, 9, 29)

    # 月末パターン 1/31 -> 7/30 (7/31 - 1日)
    d_jan = datetime.date(2026, 1, 31)
    assert calculate_plan_end_date(d_jan) == datetime.date(2026, 7, 30)

    # 互換関数 (calculate_max_review_deadline) も同値を返すこと
    assert calculate_max_review_deadline(d1) == datetime.date(2027, 2, 28)


# ====================================================================
# 2. 状態判定の起点とステータス検証（年月ベース、30日固定判定不使用）
# ====================================================================
def test_deadline_status_computation(app, auth_setup):
    """
    【受入条件】計画終了予定日と次計画開始予定日(plan_end_date + 1日)に基づく状態判定:
    例: plan_end_date = 2027/02/28
    - 2027/02/10: NORMAL (残り18日)
    - 2027/02/14: APPROACHING (残り14日以内)
    - 2027/02/28: DUE_TODAY (計画最終日、残日数0)
    - 次計画開始予定日: 2027/03/01
    - 2027/03/01～03/31: OVERDUE_WITHIN_MONTH (新計画未実施だが当月内更新猶予あり)
    - 2027/04/01以降: OVERDUE_BILLING_RISK (前月内に更新されていないため請求影響リスクあり)
    ※ 日数30日固定判定は使用せず、年月比較で判定されること
    """
    contract_a = auth_setup["contract_a"]
    plan_start = datetime.date(2026, 9, 1)
    plan_end = datetime.date(2027, 2, 28)

    plan = RetentionSupportPlan(
        contract_id=contract_a.id,
        version=1,
        overall_support_goal="ステータス検証用目標",
        start_date=plan_start,
        plan_end_date=plan_end,
        status='ACTIVE'
    )

    # 次計画開始予定日
    assert plan.next_plan_start_date == datetime.date(2027, 3, 1)

    # 1. 計画期間内 NORMAL (> 14日)
    today_normal = datetime.date(2027, 2, 10)
    st = plan.compute_deadline_status(today_normal)
    assert st["status_code"] == 'NORMAL'
    assert not st["is_overdue"]
    assert st["days_remaining"] == 18

    # 2. 計画期間内 APPROACHING (1〜14日)
    today_approaching = datetime.date(2027, 2, 14)
    st = plan.compute_deadline_status(today_approaching)
    assert st["status_code"] == 'APPROACHING'
    assert not st["is_overdue"]
    assert st["days_remaining"] == 14

    # 3. 計画期間最終日 DUE_TODAY (0日)
    today_due = datetime.date(2027, 2, 28)
    st = plan.compute_deadline_status(today_due)
    assert st["status_code"] == 'DUE_TODAY'
    assert not st["is_overdue"]
    assert st["days_remaining"] == 0

    # 4. 次計画開始予定日 2027/03/01 -> OVERDUE_WITHIN_MONTH (当月内更新猶予)
    today_mar_1 = datetime.date(2027, 3, 1)
    st = plan.compute_deadline_status(today_mar_1)
    assert st["status_code"] == 'OVERDUE_WITHIN_MONTH'
    assert st["is_overdue"]
    assert st["days_overdue"] == 1

    # 5. 当月末 2027/03/31 (31日後) -> 30日固定だとRISK判定になってしまうが、当月内なので OVERDUE_WITHIN_MONTH
    today_mar_31 = datetime.date(2027, 3, 31)
    st = plan.compute_deadline_status(today_mar_31)
    assert st["status_code"] == 'OVERDUE_WITHIN_MONTH'
    assert st["is_overdue"]
    assert st["days_overdue"] == 31

    # 6. 翌月 2027/04/01 -> OVERDUE_BILLING_RISK (請求影響リスク)
    today_apr_1 = datetime.date(2027, 4, 1)
    st = plan.compute_deadline_status(today_apr_1)
    assert st["status_code"] == 'OVERDUE_BILLING_RISK'
    assert st["is_overdue"]
    assert st["days_overdue"] == 32


# ====================================================================
# 3. 計画初回作成 & 終了予定日自動設定 & 上限ガード検証
# ====================================================================
def test_create_support_plan_success_and_guard(app, auth_setup):
    """
    【受入条件】計画初回作成:
    - plan_end_date 未指定時は自動で start_date + 6か月 - 1日 に設定される
    - 上限(6か月 - 1日)を超える日付は 400 Bad Request
    - 上限以内であれば指定可能
    """
    client = app.test_client()
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]
    headers = {"Authorization": f"Bearer {create_access_token(identity=f'staff:{staff_a.id}')}"}

    # 1. 6か月-1日超えを送信 -> 400 で拒否
    # 2026-09-01開始の場合、上限終了日は 2027-02-28。2027-03-01は超えているので拒否
    res_over = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "本人が困った時に自発的に相談できる状態を目指す",
            "start_date": "2026-09-01",
            "plan_end_date": "2027-03-01"
        }
    )
    assert res_over.status_code == 400
    assert "上限" in res_over.get_json()["msg"] or "終了予定日" in res_over.get_json()["msg"]

    # 2. 自動設定 (plan_end_date 省略) -> 2027-02-28 が設定されて 201 成功
    res_auto = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "本人が困った時に自発的に相談できる状態を目指す",
            "start_date": "2026-09-01"
        }
    )
    assert res_auto.status_code == 201
    plan_data = res_auto.get_json()["plan"]
    assert plan_data["version"] == 1
    assert plan_data["status"] == "ACTIVE"
    assert plan_data["start_date"] == "2026-09-01"
    assert plan_data["plan_end_date"] == "2027-02-28"
    assert plan_data["next_plan_start_date"] == "2027-03-01"


# ====================================================================
# 4. 早期見直し & 履歴の連続性 & 旧版内容非破壊
# ====================================================================
def test_review_support_plan_early_review_continuous_history(app, auth_setup):
    """
    【受入条件】早期見直しと履歴の連続性:
    - 6か月到達前でも随時見直し可能
    - 新計画の開始日は見直し日（例: 2026/11/01）
    - 旧計画の終了予定日は見直し日の前日（例: 2026/10/31）に調整され、適用履歴が連続する
    - 旧計画の目標や内容そのものは上書きされず保持される
    - 新しい版 (Version 2) が ACTIVE、旧版は ARCHIVED
    - 見直し理由が必須
    """
    client = app.test_client()
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]
    headers = {"Authorization": f"Bearer {create_access_token(identity=f'staff:{staff_a.id}')}"}

    # 1. Version 1 を作成 (2026/09/01 ～ 2027/02/28)
    JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="初期目標: 職場定着と基本ルーチンの確立",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id
    )

    # 見直し理由なしで見直そうとすると 400
    res_no_reason = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "新目標: 業務量増加に伴う体調管理の自律",
            "review_date": "2026-11-01",
            "review_reason": ""
        }
    )
    assert res_no_reason.status_code == 400
    assert "見直し理由" in res_no_reason.get_json()["msg"]

    # 2. 早期見直し実行 (見直し日: 2026-11-01)
    res_review = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "新目標: 業務量増加に伴う体調管理の自律",
            "review_date": "2026-11-01",
            "review_reason": "配置転換に伴う支援方針の早期見直し"
        }
    )
    assert res_review.status_code == 201
    new_plan = res_review.get_json()["plan"]
    assert new_plan["version"] == 2
    assert new_plan["status"] == "ACTIVE"
    assert new_plan["start_date"] == "2026-11-01"
    # 新計画の終了予定日: 2026-11-01 + 6か月 - 1日 = 2027-04-30
    assert new_plan["plan_end_date"] == "2027-04-30"
    assert new_plan["next_plan_start_date"] == "2027-05-01"
    assert new_plan["overall_support_goal"] == "新目標: 業務量増加に伴う体調管理の自律"
    assert new_plan["review_reason"] == "配置転換に伴う支援方針の早期見直し"

    # 3. 履歴を確認し、旧版が破壊されず連続した適用期間を持つことを確認
    res_history = client.get(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers
    )
    assert res_history.status_code == 200
    history = res_history.get_json()
    assert len(history) == 2

    # 新版 (Version 2)
    assert history[0]["version"] == 2
    assert history[0]["status"] == "ACTIVE"
    assert history[0]["start_date"] == "2026-11-01"
    assert history[0]["plan_end_date"] == "2027-04-30"

    # 旧版 (Version 1)
    assert history[1]["version"] == 1
    assert history[1]["status"] == "ARCHIVED"
    assert history[1]["overall_support_goal"] == "初期目標: 職場定着と基本ルーチンの確立"
    assert history[1]["start_date"] == "2026-09-01"
    # 旧計画の終了日は、新計画開始日(2026-11-01)の前日(2026-10-31)となり、連続していること
    assert history[1]["plan_end_date"] == "2026-10-31"


# ====================================================================
# 5. ACTIVE計画1件制約 (DBレベル部分一意インデックス)
# ====================================================================
def test_db_enforces_single_active_plan(app, auth_setup):
    """
    【受入条件】DB部分一意インデックス:
    - 1つの契約に ACTIVE な計画を2件登録しようとすると IntegrityError が発生する
    """
    contract_a = auth_setup["contract_a"]

    plan1 = RetentionSupportPlan(
        contract_id=contract_a.id,
        version=1,
        overall_support_goal="計画1",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        status='ACTIVE'
    )
    db.session.add(plan1)
    db.session.commit()

    with pytest.raises(IntegrityError):
        plan2 = RetentionSupportPlan(
            contract_id=contract_a.id,
            version=2,
            overall_support_goal="計画2",
            start_date=datetime.date(2026, 9, 1),
            plan_end_date=datetime.date(2027, 2, 28),
            status='ACTIVE' # 重複してACTIVE
        )
        db.session.add(plan2)
        db.session.commit()
    db.session.rollback()


# ====================================================================
# 6. 初月月次レポートとの接続 & 通常月優先
# ====================================================================
def test_first_month_report_proposes_active_plan_goal(app, auth_setup):
    """
    【受入条件】月次レポートとの接続:
    - 前月確定レポートがない初月は、ACTIVE計画の overall_support_goal が初期提案値になる
    - 前月確定レポートがある通常月は、前月の future_support_plan が優先される
    """
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]

    # 支援計画を作成
    JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="職場での主体的SOS発信力を身につける",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id
    )

    # 1. 前月確定レポートがない初月(2026-09) -> 支援計画の目標が初期提案値になる
    preview_sep = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-09")
    assert preview_sep["support_goal"] == "職場での主体的SOS発信力を身につける"

    # 2. 9月レポートを確定保存 (future_support_plan あり)
    JobRetentionService.save_monthly_report(
        contract_id=contract_a.id,
        supporter_id=staff_a.id,
        year_month="2026-09",
        report_data={
            "support_goal": "職場での主体的SOS発信力を身につける",
            "future_support_plan": "10月は業務量増大時の休憩取得状況を確認する"
        },
        finalize=True
    )

    # 3. 翌月(2026-10) -> 前月確定レポートの future_support_plan が優先される (計画目標で上書きされない)
    preview_oct = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-10")
    assert preview_oct["support_goal"] == "10月は業務量増大時の休憩取得状況を確認する"


# ====================================================================
# 7. 未作成状態の Fail Closed (自動生成禁止)
# ====================================================================
def test_uncreated_plan_status_does_not_autogenerate(app, auth_setup):
    """
    【受入条件】計画未作成状態:
    - 計画が存在しない場合、has_plan=False で返り、システムが勝手に作成しない
    """
    client = app.test_client()
    contract_b = auth_setup["contract_b"]
    staff_b = auth_setup["staff_b"]
    headers = {"Authorization": f"Bearer {create_access_token(identity=f'staff:{staff_b.id}')}"}

    res = client.get(
        f"/api/job-retention/contracts/{contract_b.id}/support-plan/active",
        headers=headers
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["has_plan"] is False
    assert data["plan"] is None

    # DB上にも自動生成されたレコードが存在しないこと
    count = RetentionSupportPlan.query.filter_by(contract_id=contract_b.id).count()
    assert count == 0
