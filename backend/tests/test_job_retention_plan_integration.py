# backend/tests/test_job_retention_plan_integration.py

import pytest
import datetime
from backend.app.extensions import db
from backend.app.models import (
    JobRetentionContract, SupportPlan, LongTermGoal, ShortTermGoal,
    RetentionSupportPlanDetail, RetentionSupportPlanItem, RetentionSupportPlanSourceLink,
    RetentionUserVoiceLog, RetentionEmployerFeedbackLog, RetentionSupportActionLog,
    MonthlyRetentionReport
)
from backend.app.services.job_retention_service import JobRetentionService
from backend.tests.test_job_retention_auth import auth_setup, get_headers


def test_support_plan_integration_and_goal_models(app, auth_setup):
    """
    【仕様検証】
    1. 既存 SupportPlan を個別支援計画の共通親として利用
    2. LongTermGoal / ShortTermGoal に本文および set_year_month / target_year_month (YYYY-MM) を保持
    3. RetentionSupportPlanDetail に review_date / review_reason およびスナップショットを保持
       （review_date を SupportPlan.activated_at や explained_at に流用しないこと）
    4. RetentionSupportPlanItem が short_term_goal_id と明示的に接続
    5. SupportPlan.office_service_configuration_id および created_by_id が正しく保存されること
    """
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]

    start_d = datetime.date(2026, 9, 1)
    end_d = datetime.date(2027, 2, 28)
    review_d = datetime.date(2026, 9, 1)
    review_reason = "就職後の初期計画策定"

    items_input = [
        {
            "item_number": 1,
            "challenge_topic": "通勤ラッシュ時の体調管理",
            "support_policy": "満員電車を避ける時差出勤の定着",
            "support_content": "始業前30分前の出勤と体調確認",
            "support_period_start": start_d,
            "support_period_end": end_d,
            "support_frequency": "週1回",
            "role_sharing": "本人: 体調記録 / 企業: 時差出勤許可 / 支援員: 月次確認"
        },
        {
            "item_number": 2,
            "challenge_topic": "職場での業務指示の確認",
            "support_policy": "指示事項のメモ取りと復唱の徹底",
            "support_content": "業務指示メモ帳の活用と不明点質問ルールの運用",
            "support_period_start": start_d,
            "support_period_end": end_d,
            "support_frequency": "月2回",
            "role_sharing": "本人: メモ記入 / 企業: 復唱確認"
        }
    ]

    source_links_input = [
        {
            "target_field": "situation_info.user_wishes",
            "source_type": "USER_VOICE",
            "source_id": 1,
            "excerpt_text": "時差出勤で通勤できれば体調が安定します"
        }
    ]

    detail_fields_input = {
        "physical_work_environment": "空調の効いたデスク席、休憩スペース近接",
        "human_work_environment": "指導担当者が隣席に配置され、声かけがしやすい環境",
        "user_wishes": "長く安定して働き続けたい",
        "health_condition": "服薬管理良好、睡眠時間7時間確保"
    }

    # サービス呼び出しで作成
    plan_detail = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="職場環境に慣れ、体調を安定させて勤怠を維持する",
        plan_end_date=end_d,
        review_date=review_d,
        review_reason=review_reason,
        start_date=start_d,
        supporter_id=staff_a.id,
        items_data=items_input,
        source_links_data=source_links_input,
        detail_fields=detail_fields_input
    )

    # 1. 共通親 SupportPlan の検証
    sp = plan_detail.support_plan
    assert sp is not None
    assert sp.user_id == contract_a.user_id
    assert sp.plan_version == 1
    assert sp.plan_status == 'ACTIVE'
    assert sp.plan_start_date == start_d
    assert sp.plan_end_date == end_d
    assert sp.office_service_configuration_id == contract_a.office_service_configuration_id
    assert sp.created_by_id == staff_a.id
    # activated_at は計画有効化日 (start_d) であり、review_date の流用ではないこと
    assert sp.activated_at == start_d

    # 2. LongTermGoal / ShortTermGoal の検証
    assert len(sp.long_term_goals) == 1
    ltg = sp.long_term_goals[0]
    assert ltg.description == "職場環境に慣れ、体調を安定させて勤怠を維持する"
    assert ltg.set_year_month == "2026-09"
    assert ltg.target_year_month == "2027-02"

    assert len(ltg.short_term_goals) == 1
    stg = ltg.short_term_goals[0]
    assert stg.description == "職場環境に慣れ、体調を安定させて勤怠を維持する"
    assert stg.set_year_month == "2026-09"
    assert stg.target_year_month == "2027-02"

    # 3. RetentionSupportPlanDetail の検証
    assert plan_detail.retention_contract_id == contract_a.id
    assert plan_detail.overall_support_goal == "職場環境に慣れ、体調を安定させて勤怠を維持する"
    assert plan_detail.review_date == review_d
    assert plan_detail.review_reason == review_reason
    assert plan_detail.physical_work_environment == "空調の効いたデスク席、休憩スペース近接"
    assert plan_detail.human_work_environment == "指導担当者が隣席に配置され、声かけがしやすい環境"
    assert plan_detail.user_wishes == "長く安定して働き続けたい"

    # 4. RetentionSupportPlanItem の検証 (ShortTermGoal接続)
    assert len(plan_detail.items) == 2
    item1 = plan_detail.items[0]
    assert item1.item_number == 1
    assert item1.short_term_goal_id == stg.id
    assert item1.challenge_topic == "通勤ラッシュ時の体調管理"
    assert item1.support_frequency == "週1回"

    item2 = plan_detail.items[1]
    assert item2.item_number == 2
    assert item2.short_term_goal_id == stg.id

    # 5. 出所リンクの検証
    assert len(plan_detail.source_links) == 1
    link = plan_detail.source_links[0]
    assert link.source_type == "USER_VOICE"
    assert link.target_field == "situation_info.user_wishes"
    assert "時差出勤" in link.excerpt_text


def test_input_assistance_and_detail_api(app, client, auth_setup):
    """
    【API検証】
    1. GET /contracts/<id>/support-plan/assistance-data: 一次情報候補と確定事実スナップショットの返却
    2. GET /contracts/<id>/support-plans/<plan_id>/detail: 厚労省様式2の全項目返却
    """
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]
    headers = get_headers(f"staff:{staff_a.id}")

    # 事前に就労エピソード・一次情報を投入
    from backend.app.models import RetentionEmploymentEpisode
    ep = RetentionEmploymentEpisode(
        contract_id=contract_a.id,
        episode_number=1,
        workplace_name="株式会社テスト企業",
        job_title="事務職",
        job_start_date=datetime.date(2026, 9, 1),
        work_conditions="週5日 30時間"
    )
    voice = RetentionUserVoiceLog(
        contract_id=contract_a.id,
        help_topic="職場での人間関係",
        raw_voice="指導担当の方が丁寧に教えてくださり助かっています。"
    )
    feedback = RetentionEmployerFeedbackLog(
        contract_id=contract_a.id,
        contact_person="人事部長",
        workplace_observation="真面目に業務に取り組んでおり、出勤率も100%です。"
    )
    action = RetentionSupportActionLog(
        contract_id=contract_a.id,
        supporter_id=staff_a.id,
        action_date=datetime.date(2026, 9, 4),
        has_user_interview=True,
        confirmed_situation="職場のルールを順調に習得中",
        provided_support="日報の書き方についてアドバイスを実施"
    )
    db.session.add_all([ep, voice, feedback, action])
    db.session.commit()

    # 1. 入力支援 API の呼び出し
    resp = client.get(
        f"/api/job-retention/contracts/{contract_a.id}/support-plan/assistance-data",
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.get_json()

    # 確定事実スナップショットの確認
    assert "user_info_snapshot" in data
    assert "employment_info_snapshot" in data
    assert "office_info_snapshot" in data
    assert data["employment_info_snapshot"]["employer_name"] == "株式会社テスト企業"

    # 一次情報候補の確認
    cands = data["candidates"]
    assert len(cands["voice_candidates"]) >= 1
    assert "丁寧に教えてくださり" in cands["voice_candidates"][0]["content"]
    assert len(cands["feedback_candidates"]) >= 1
    assert "真面目に業務" in cands["feedback_candidates"][0]["content"]
    assert len(cands["action_candidates"]) >= 1

    # 2. 計画作成
    create_resp = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "業務習熟と自己管理の確立",
            "start_date": "2026-09-01",
            "plan_end_date": "2027-02-28",
            "review_date": "2026-09-04",
            "review_reason": "就職初期支援計画",
            "detail_fields": {
                "physical_work_environment": "専用デスクあり",
                "user_wishes": "ミスなく一人で作業できるようになりたい"
            },
            "items_data": [
                {
                    "item_number": 1,
                    "challenge_topic": "作業手順の定着",
                    "support_policy": "チェックリストの活用",
                    "support_content": "日々の作業開始前確認"
                }
            ]
        }
    )
    assert create_resp.status_code == 201
    plan_id = create_resp.get_json()["plan"]["id"]

    # 3. 様式2 詳細 API の呼び出し
    detail_resp = client.get(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans/{plan_id}/detail",
        headers=headers
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.get_json()

    assert detail_data["overall_support_goal"] == "業務習熟と自己管理の確立"
    assert detail_data["version"] == 1
    assert detail_data["status"] == 'ACTIVE'
    assert detail_data["start_date"] == "2026-09-01"
    assert detail_data["plan_end_date"] == "2027-02-28"
    assert detail_data["review_date"] == "2026-09-04"
    assert detail_data["review_reason"] == "就職初期支援計画"
    assert detail_data["employment_info"]["physical_work_environment"] == "専用デスクあり"
    assert len(detail_data["items"]) == 1
    assert detail_data["items"][0]["challenge_topic"] == "作業手順の定着"
    assert detail_data["long_term_goal"]["set_year_month"] == "2026-09"


def test_plan_review_workflow_and_detail_continuity(app, auth_setup):
    """
    【随時見直し・版管理の統合検証】
    1. 初回作成 (v1) -> SupportPlan(ACTIVE) + Detail
    2. 早期見直し (v2) -> 旧SupportPlan(ARCHIVED), 新SupportPlan(ACTIVE, v2, based_on=v1)
    3. review_date / review_reason が新Detailに記録され、SupportPlan.activated_at は新開始日と一致
    4. 既存 Goal / Item の関連付けが新版でも整合すること
    """
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]

    # 1. 初回版 (2026/09/01 - 2027/02/28)
    d1 = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="初期定着目標",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id
    )
    sp1 = d1.support_plan
    assert sp1.plan_version == 1
    assert sp1.plan_status == 'ACTIVE'
    assert sp1.plan_end_date == datetime.date(2027, 2, 28)

    # 2. 早期見直し (2026/11/15)
    d2 = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="早期見直し後の定着目標",
        review_date=datetime.date(2026, 11, 15),
        review_reason="業務負荷の増大に伴う配慮見直し",
        plan_end_date=datetime.date(2027, 5, 14),
        supporter_id=staff_a.id
    )
    sp2 = d2.support_plan
    assert sp2.plan_version == 2
    assert sp2.plan_status == 'ACTIVE'
    assert sp2.plan_start_date == datetime.date(2026, 11, 15)
    assert sp2.plan_end_date == datetime.date(2027, 5, 14)
    assert sp2.based_on_plan_id == sp1.id

    # 旧版が ARCHIVED に更新され、期間が連続 (2026/11/14終了)
    assert sp1.plan_status == 'ARCHIVED'
    assert sp1.plan_end_date == datetime.date(2026, 11, 14)

    # Detail に review_date / review_reason が保持されること
    assert d2.review_date == datetime.date(2026, 11, 15)
    assert d2.review_reason == "業務負荷の増大に伴う配慮見直し"
    # SupportPlan.activated_at は新計画の開始日
    assert sp2.activated_at == datetime.date(2026, 11, 15)

    # ACTIVEな計画取得で d2 が取得できること
    active = JobRetentionService.get_active_support_plan(contract_a.id)
    assert active.id == d2.id
    assert active.version == 2

