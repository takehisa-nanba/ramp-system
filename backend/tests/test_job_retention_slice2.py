# backend/tests/test_job_retention_slice2.py

import pytest
import datetime
import dateutil.relativedelta
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models import (
    JobRetentionContract, RetentionSupportPlan,
    calculate_max_review_deadline, MonthlyRetentionReport
)
from backend.app.services.job_retention_service import JobRetentionService
from backend.tests.test_job_retention_auth import auth_setup, get_headers


# ====================================================================
# 1. 6か月計算 & 期限ステータス計算の単体検証
# ====================================================================
def test_calculate_max_review_deadline():
    """暦上の6か月後（月末調整考慮）が正しく計算されること"""
    # 通常
    d1 = datetime.date(2026, 9, 1)
    assert calculate_max_review_deadline(d1) == datetime.date(2027, 3, 1)

    # 8月31日 -> 翌年2月28日（月末調整）
    d2 = datetime.date(2026, 8, 31)
    assert calculate_max_review_deadline(d2) == datetime.date(2027, 2, 28)

    # うるう年の場合: 2023年8月31日 -> 2024年2月29日
    d3 = datetime.date(2023, 8, 31)
    assert calculate_max_review_deadline(d3) == datetime.date(2024, 2, 29)


def test_deadline_status_computation(app, auth_setup):
    """
    【受入条件】期限ステータス判定:
    - NORMAL: 15日以上先
    - APPROACHING: 14日以内
    - DUE_TODAY: 当日 (残日数0)
    - OVERDUE_WITHIN_MONTH: 超過後1か月以内 (-1〜-30日)
    - OVERDUE_BILLING_RISK: 大幅超過 (-31日以下)
    """
    contract_a = auth_setup["contract_a"]
    today = datetime.date(2026, 9, 15)

    plan = RetentionSupportPlan(
        contract_id=contract_a.id,
        version=1,
        overall_support_goal="ステータス検証用目標",
        start_date=today,
        next_review_deadline=today + datetime.timedelta(days=20),
        status='ACTIVE'
    )

    # NORMAL (> 14日)
    plan.next_review_deadline = today + datetime.timedelta(days=20)
    assert plan.compute_deadline_status(today)["status_code"] == 'NORMAL'
    assert not plan.compute_deadline_status(today)["is_overdue"]

    # APPROACHING (1〜14日)
    plan.next_review_deadline = today + datetime.timedelta(days=14)
    assert plan.compute_deadline_status(today)["status_code"] == 'APPROACHING'
    plan.next_review_deadline = today + datetime.timedelta(days=1)
    assert plan.compute_deadline_status(today)["status_code"] == 'APPROACHING'

    # DUE_TODAY (0日)
    plan.next_review_deadline = today
    assert plan.compute_deadline_status(today)["status_code"] == 'DUE_TODAY'
    assert not plan.compute_deadline_status(today)["is_overdue"]

    # OVERDUE_WITHIN_MONTH (-1〜-30日)
    plan.next_review_deadline = today - datetime.timedelta(days=1)
    assert plan.compute_deadline_status(today)["status_code"] == 'OVERDUE_WITHIN_MONTH'
    assert plan.compute_deadline_status(today)["is_overdue"]
    plan.next_review_deadline = today - datetime.timedelta(days=30)
    assert plan.compute_deadline_status(today)["status_code"] == 'OVERDUE_WITHIN_MONTH'

    # OVERDUE_BILLING_RISK (<-30日)
    plan.next_review_deadline = today - datetime.timedelta(days=31)
    assert plan.compute_deadline_status(today)["status_code"] == 'OVERDUE_BILLING_RISK'
    assert plan.compute_deadline_status(today)["is_overdue"]


# ====================================================================
# 2. 計画初回作成 & 6か月上限ガード検証
# ====================================================================
def test_create_support_plan_success_and_guard(app, auth_setup):
    """
    【受入条件】計画初回作成 & 6か月上限:
    - 基準日+6か月以内の期限は作成成功 (Version 1)
    - 6か月を超える期限は 400 Bad Request
    """
    client = app.test_client()
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]
    headers = {"Authorization": f"Bearer {create_access_token(identity=f'staff:{staff_a.id}')}"}

    # 1. 6か月超えを送信 -> 400 で拒否
    res_over = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "本人が困った時に自発的に相談できる状態を目指す",
            "start_date": "2026-09-01",
            "next_review_deadline": "2027-03-02" # 6か月超過（上限は2027-03-01）
        }
    )
    assert res_over.status_code == 400
    assert "6か月以内" in res_over.get_json()["msg"]

    # 2. 6か月ちょうど（上限ギリギリ）で送信 -> 201 成功
    res_ok = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "本人が困った時に自発的に相談できる状態を目指す",
            "start_date": "2026-09-01",
            "next_review_deadline": "2027-03-01"
        }
    )
    assert res_ok.status_code == 201
    plan_data = res_ok.get_json()["plan"]
    assert plan_data["version"] == 1
    assert plan_data["status"] == "ACTIVE"
    assert plan_data["overall_support_goal"] == "本人が困った時に自発的に相談できる状態を目指す"
    assert plan_data["next_review_deadline"] == "2027-03-01"


# ====================================================================
# 3. 随時見直し & 旧版アーカイブ & バージョン連番
# ====================================================================
def test_review_support_plan_increments_version_and_archives_old(app, auth_setup):
    """
    【受入条件】随時見直し:
    - 期限前でもいつでも見直し可能
    - 新しい版 (Version 2) が ACTIVE になり、旧版は ARCHIVED になる
    - 過去の計画は上書きされず履歴に残る
    - 見直し理由の入力必須
    - 見直し日から6か月上限ガード
    """
    client = app.test_client()
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]
    headers = {"Authorization": f"Bearer {create_access_token(identity=f'staff:{staff_a.id}')}"}

    # Version 1 を作成
    JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="初期目標: 職場定着と基本ルーチンの確立",
        start_date=datetime.date(2026, 9, 1),
        next_review_deadline=datetime.date(2027, 3, 1),
        supporter_id=staff_a.id
    )

    # 見直し理由なしで見直そうとすると 400
    res_no_reason = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "新目標: 業務量増加に伴う体調管理の自律",
            "review_date": "2026-11-01",
            "next_review_deadline": "2027-05-01",
            "review_reason": "" # 空文字
        }
    )
    assert res_no_reason.status_code == 400
    assert "見直し理由" in res_no_reason.get_json()["msg"]

    # 見直し日(2026-11-01)から6か月超(2027-05-02)は 400
    res_over_review = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "新目標: 業務量増加に伴う体調管理の自律",
            "review_date": "2026-11-01",
            "next_review_deadline": "2027-05-02",
            "review_reason": "配置転換に伴う支援方針の見直し"
        }
    )
    assert res_over_review.status_code == 400

    # 正常な見直し実行 (期限前随時見直し)
    res_review = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "新目標: 業務量増加に伴う体調管理の自律",
            "review_date": "2026-11-01",
            "next_review_deadline": "2027-05-01",
            "review_reason": "配置転換に伴う支援方針の見直し"
        }
    )
    assert res_review.status_code == 201
    new_plan_data = res_review.get_json()["plan"]
    assert new_plan_data["version"] == 2
    assert new_plan_data["status"] == "ACTIVE"
    assert new_plan_data["overall_support_goal"] == "新目標: 業務量増加に伴う体調管理の自律"
    assert new_plan_data["review_reason"] == "配置転換に伴う支援方針の見直し"

    # 履歴を確認
    res_history = client.get(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers
    )
    assert res_history.status_code == 200
    history = res_history.get_json()
    assert len(history) == 2
    assert history[0]["version"] == 2
    assert history[0]["status"] == "ACTIVE"
    assert history[1]["version"] == 1
    assert history[1]["status"] == "ARCHIVED"
    assert history[1]["overall_support_goal"] == "初期目標: 職場定着と基本ルーチンの確立"


# ====================================================================
# 4. ACTIVE計画1件制約 (DBレベル部分一意インデックス)
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
        next_review_deadline=datetime.date(2027, 3, 1),
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
            next_review_deadline=datetime.date(2027, 3, 1),
            status='ACTIVE' # 重複してACTIVE
        )
        db.session.add(plan2)
        db.session.commit()
    db.session.rollback()


# ====================================================================
# 5. 初月月次レポートとの接続 & 通常月優先
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
        next_review_deadline=datetime.date(2027, 3, 1),
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
# 6. 未作成状態の Fail Closed (自動生成禁止)
# ====================================================================
def test_uncreated_plan_status_does_not_autogenerate(app, auth_setup):
    """
    【受入条件】計画未作成状態:
    - 計画が存在しない場合、has_plan=False で返り、システムが勝手に作成しない
    """
    client = app.test_client()
    contract_b = auth_setup["contract_b"] # 計画未作成の別事業所契約
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
