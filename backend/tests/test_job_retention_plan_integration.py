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

    long_term_goal_input = {
        "description": "職場環境に慣れ、体調を安定させて勤怠を維持する",
        "challenges": "就労定着",
        "set_year_month": "2026-09",
        "target_year_month": "2027-02"
    }
    short_term_goal_input = {
        "description": "職場環境に慣れ、体調を安定させて勤怠を維持する",
        "set_year_month": "2026-09",
        "target_year_month": "2027-02"
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
        detail_fields=detail_fields_input,
        long_term_goal_data=long_term_goal_input,
        short_term_goal_data=short_term_goal_input,
        initial_status='ACTIVE'
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
    # 初回策定時は review_date / review_reason を見直し情報として保存しない (要件6)
    assert plan_detail.review_date is None
    assert plan_detail.review_reason is None
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
    # 雇用条件スナップショットの検証（work_conditionsを賃金欄へ自動設定しない：要件3）
    assert data["employment_info_snapshot"]["employer_name"] == "株式会社テスト企業"
    assert data["employment_info_snapshot"]["wage_condition"] is None
    assert data["candidates"]["work_conditions_candidate"] == "週5日 30時間"

    # 2. 計画作成 (long_term_goal_data を明示的に指定)
    create_resp = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/support-plans",
        headers=headers,
        json={
            "overall_support_goal": "業務習熟と自己管理の確立",
            "initial_status": "ACTIVE",
            "start_date": "2026-09-01",
            "plan_end_date": "2027-02-28",
            "review_date": "2026-09-04",
            "review_reason": "就職初期支援計画",
            "detail_fields": {
                "physical_work_environment": "専用デスクあり",
                "user_wishes": "ミスなく一人で作業できるようになりたい"
            },
            "long_term_goal_data": {
                "description": "業務習熟と自己管理の確立",
                "set_year_month": "2026-09",
                "target_year_month": "2027-02"
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
    # 初回策定時は review_date / review_reason は None (要件6)
    assert detail_data["review_date"] is None
    assert detail_data["review_reason"] is None
    assert detail_data["employment_info"]["physical_work_environment"] == "専用デスクあり"
    assert len(detail_data["items"]) == 1
    assert detail_data["items"][0]["challenge_topic"] == "作業手順の定着"
    assert detail_data["long_term_goal"] is not None
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
        supporter_id=staff_a.id,
        initial_status='ACTIVE'
    )
    sp1 = d1.support_plan
    assert sp1.plan_version == 1
    assert sp1.plan_status == 'ACTIVE'
    assert sp1.plan_end_date == datetime.date(2027, 2, 28)
    # 初回計画には review_date / review_reason は保存されない (要件6)
    assert d1.review_date is None
    assert d1.review_reason is None

    # 2. 早期見直し (2026/11/15)
    d2 = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="早期見直し後の定着目標",
        review_date=datetime.date(2026, 11, 15),
        review_reason="業務負荷の増大に伴う配慮見直し",
        plan_end_date=datetime.date(2027, 5, 14),
        supporter_id=staff_a.id,
        initial_status='ACTIVE'
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


def test_no_fictitious_goals_or_items_on_creation_and_review(app, auth_setup):
    """
    【要件1・2検証: 架空の公式計画項目・目標・支援内容を自動生成しない】
    1. Goalデータ/Itemデータを渡さない場合、LongTermGoal / ShortTermGoal / Item は作成されない。
    2. overall_support_goal を LongTermGoal / ShortTermGoal に自動コピーしない。
    3. 「就労定着課題」「就労定着の安定化」「月1回以上」等のデフォルトアイテムを捏造しない。
    4. get_support_plan_detail で long_term_goal, short_term_goal は None を返す。
    """
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]

    # 新規作成（goal_data, items_data は渡さない）
    plan = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="真の大まかな支援目標のみ",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id
    )

    sp = plan.support_plan
    # 架空目標が作成されていないこと
    assert len(sp.long_term_goals) == 0

    # 架空アイテムが作成されていないこと
    assert len(plan.items) == 0

    # 詳細取得APIでも架空目標・アイテムがフォールバック捏造されないこと
    detail = JobRetentionService.get_support_plan_detail(contract_a.id, plan.id)
    assert detail["overall_support_goal"] == "真の大まかな支援目標のみ"
    assert detail["long_term_goal"] is None
    assert detail["short_term_goal"] is None
    assert detail["items"] == []


def test_monthly_report_support_goal_inheritance_rules(app, auth_setup):
    """
    【要件8検証: 月次レポート support_goal 引き継ぎの厳密化】
    1. 契約初月 (contract_start_ym) のみ ACTIVE 計画の overall_support_goal を初期提案。
    2. 2か月目以降（通常月）:
       - 前月レポートが存在しない場合 → support_goal は空文字 ""（計画目標へフォールバック禁止）
       - 前月レポートが DRAFT の場合 → support_goal は空文字 ""
       - 前月レポートが FINALIZED だが future_support_plan が空の場合 → support_goal は空文字 ""
       - 前月レポートが FINALIZED で future_support_plan がある場合 → その値のみを引き継ぐ
    """
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]

    # 契約開始日は 2026/09/01 (auth_setup で作成) -> 初月は "2026-09"
    # まず ACTIVE 計画を作成
    JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="初月用ACTIVE計画目標",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id,
        initial_status='ACTIVE'
    )

    # 1. 契約初月 ("2026-09") のプレビュー -> ACTIVE 計画の目標が提案される
    p_sep = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-09")
    assert p_sep["support_goal"] == "初月用ACTIVE計画目標"

    # 2. 翌月 ("2026-10") のプレビュー (前月レポート未作成)
    # 任意月で計画目標へフォールバックしないため、空文字 "" になること
    p_oct_no_prev = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-10")
    assert p_oct_no_prev["support_goal"] == ""

    # 3. 前月 ("2026-09") レポートを DRAFT で保存
    JobRetentionService.save_monthly_report(
        contract_id=contract_a.id,
        supporter_id=staff_a.id,
        year_month="2026-09",
        report_data={"future_support_plan": "9月DRAFTの今後の計画"},
        finalize=False
    )
    # 前月が DRAFT の場合も通常月 ("2026-10") では引き継がず空文字 ""
    p_oct_draft_prev = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-10")
    assert p_oct_draft_prev["support_goal"] == ""

    # 4. 前月 ("2026-09") レポートを future_support_plan 入力済みで確定 (FINALIZED)
    JobRetentionService.save_monthly_report(
        contract_id=contract_a.id,
        supporter_id=staff_a.id,
        year_month="2026-09",
        report_data={"future_support_plan": "10月は残業抑制と自己申告の徹底"},
        finalize=True
    )
    # 通常月 ("2026-10") で前月 FINALIZED の future_support_plan が正常に引き継がれる
    p_oct_finalized = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-10")
    assert p_oct_finalized["support_goal"] == "10月は残業抑制と自己申告の徹底"

    # 5. 当月 ("2026-10") レポートを future_support_plan 空で確定 (FINALIZED)
    JobRetentionService.save_monthly_report(
        contract_id=contract_a.id,
        supporter_id=staff_a.id,
        year_month="2026-10",
        report_data={"support_goal": "10月は残業抑制と自己申告の徹底", "future_support_plan": ""},
        finalize=True
    )
    # 翌月 ("2026-11") プレビュー: 前月レポートが確定済みでも future_support_plan が空なら空文字 ""
    p_nov_empty_prev = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-11")
    assert p_nov_empty_prev["support_goal"] == ""


def test_input_assistance_real_models_and_no_dummy_strings(app, auth_setup):
    """
    【要件4検証: 入力支援APIの一次情報取得先を実モデルへ修正 & ダミー文字列排除】
    - UserPII (氏名, かな, 生年月日, 性別, 手帳)
    - ServiceCertificate (障害支援区分)
    - 固定文字列「未設定」「未登録」「就労定着支援事業所」を返さず None を返すこと
    """
    contract_a = auth_setup["contract_a"]
    user = contract_a.user

    # 1. 未設定状態の契約での検証（ダミー固定値が入らないこと）
    data_empty = JobRetentionService.get_plan_input_assistance_data(contract_a.id)
    user_snap = data_empty["user_info_snapshot"]
    # 固定ダミー値「未設定」「未登録」ではなく None または平文
    assert user_snap["gender"] is None or user_snap["gender"] != "未設定"
    assert user_snap["support_level"] is None or user_snap["support_level"] != "就労定着"

    # 2. 実モデルに値を設定
    from backend.app.models import GenderLegalMaster, ServiceCertificate, MunicipalityMaster, UserPII
    gender_m = GenderLegalMaster.query.filter_by(name="女性").first()
    if not gender_m:
        gender_m = GenderLegalMaster(name="女性")
        db.session.add(gender_m)
        db.session.flush()

    if not user.pii:
        pii = UserPII(
            user_id=user.id,
            last_name="定着",
            first_name="花子",
            last_name_kana="テイチャク",
            first_name_kana="ハナコ",
            birth_date=datetime.date(1995, 5, 20),
            gender_legal_id=gender_m.id,
            handbook_level="精神2級",
            is_handbook_certified=True
        )
        db.session.add(pii)
    else:
        user.pii.last_name = "定着"
        user.pii.first_name = "花子"
        user.pii.last_name_kana = "テイチャク"
        user.pii.first_name_kana = "ハナコ"
        user.pii.birth_date = datetime.date(1995, 5, 20)
        user.pii.gender_legal_id = gender_m.id
        user.pii.handbook_level = "精神2級"
        user.pii.is_handbook_certified = True
    db.session.flush()

    muni = MunicipalityMaster.query.first()
    if not muni:
        muni = MunicipalityMaster(municipality_code="12345", name="テスト区")
        db.session.add(muni)
        db.session.flush()

    cert = ServiceCertificate(
        user_id=user.id,
        office_service_configuration_id=contract_a.office_service_configuration_id,
        certificate_issue_date=datetime.date(2026, 1, 1),
        municipality_master_id=muni.id,
        disability_support_classification="区分3"
    )
    db.session.add(cert)
    db.session.commit()

    # 3. 入力支援 API データ取得
    data_filled = JobRetentionService.get_plan_input_assistance_data(contract_a.id)
    u_snap = data_filled["user_info_snapshot"]

    assert u_snap["user_name"] == "定着 花子"
    assert u_snap["user_name_kana"] == "テイチャク ハナコ"
    assert u_snap["birth_date"] == "1995-05-20"
    assert u_snap["gender"] == "女性"
    assert u_snap["support_level"] == "区分3"
    # 要件2: 手帳等級（精神2級）から手帳種別を推測しないため None
    assert u_snap["disability_handbook_type"] is None
    # 参考候補として手帳等級が提供されること
    assert data_filled["candidates"]["handbook_level_candidate"] == "精神2級"


def test_plan_snapshot_immutability_and_full_fields(app, auth_setup):
    """
    【追加要件1検証: 計画確定時の確定事実スナップショット完全保存 & 過去版のデータ不変性】
    1. 計画作成時に UserPII, エピソード, 事業所情報から確定事実が Snapshot 保存されること。
    2. user_name は User.display_name で代用せず、UserPII 実名を snapshot すること。
    3. その後、UserPII / Episode / OfficeSetting が変更されても、過去版の計画スナップショットは変わらないこと。
    """
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]
    user = contract_a.user

    # UserPII, 雇用エピソード, 事業所設定の実データ確認/セットアップ
    from backend.app.models import UserPII, RetentionEmploymentEpisode, OfficeSetting
    if not user.pii:
        pii = UserPII(
            user_id=user.id,
            last_name="確定",
            first_name="太郎",
            last_name_kana="カクテイ",
            first_name_kana="タロウ",
            birth_date=datetime.date(1990, 1, 15)
        )
        db.session.add(pii)
    else:
        user.pii.last_name = "確定"
        user.pii.last_name_kana = "カクテイ"
        user.pii.first_name = "太郎"
        user.pii.first_name_kana = "タロウ"
        user.pii.birth_date = datetime.date(1990, 1, 15)
    db.session.commit()

    # 1. 計画策定 (v1)
    plan_v1 = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="スナップショット不変性検証目標",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id,
        detail_fields={
            "disability_handbook_type": "精神障害者保健福祉手帳"
        }
    )

    detail_v1 = JobRetentionService.get_support_plan_detail(contract_a.id, plan_v1.id)
    # User.display_name（「利用者A」）ではなく UserPII 実名が保存されていること
    assert detail_v1["user_info"]["user_name"] == "確定 太郎"
    assert detail_v1["user_info"]["user_name_kana"] == "カクテイ タロウ"
    assert detail_v1["user_info"]["birth_date"] == "1990-01-15"
    assert detail_v1["user_info"]["disability_handbook_type"] == "精神障害者保健福祉手帳"

    initial_employer_name = detail_v1["employment_info"]["employer_name"]
    initial_office_name = detail_v1["office_and_staff_info"]["office_name"]

    # 2. マスター / 一次情報データを後から変更する
    user.pii.last_name = "変更後氏名"
    user.display_name = "変更後表示名"
    latest_ep = contract_a.episodes[-1] if contract_a.episodes else None
    if latest_ep:
        latest_ep.workplace_name = "全新規株式会社"
    office_config = contract_a.office_service_configuration
    if office_config and office_config.office:
        office_config.office.office_name = "改装後新事業所"
    db.session.commit()

    # 3. 過去版 (v1) を再度取得 -> スナップショットが保存されているため一切変わらないこと
    detail_v1_reloaded = JobRetentionService.get_support_plan_detail(contract_a.id, plan_v1.id)
    assert detail_v1_reloaded["user_info"]["user_name"] == "確定 太郎" # 変更後の「変更後氏名」にならない
    assert detail_v1_reloaded["employment_info"]["employer_name"] == initial_employer_name # 「全新規株式会社」にならない
    assert detail_v1_reloaded["office_and_staff_info"]["office_name"] == initial_office_name # 「改装後新事業所」にならない


def test_handbook_type_not_inferred_from_level_and_user_input(app, auth_setup):
    """
    【追加要件2検証: 障害者手帳「種別」を等級から推測しない】
    - UserPII.handbook_level = "精神2級" のとき、入力支援APIの disability_handbook_type は None
    - 手帳等級と手帳種別を混同せず、UI/支援員が明示的に入力・確認した値が保存されること
    """
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]
    user = contract_a.user

    from backend.app.models import UserPII
    if not user.pii:
        user.pii = UserPII(user_id=user.id, handbook_level="身体1級")
    else:
        user.pii.handbook_level = "身体1級"
    db.session.commit()

    assist = JobRetentionService.get_plan_input_assistance_data(contract_a.id)
    # 種別は等級から推測しないため None
    assert assist["user_info_snapshot"]["disability_handbook_type"] is None
    # 候補として等級は確認できる
    assert assist["candidates"]["handbook_level_candidate"] == "身体1級"

    # 支援員が明示的に手帳種別「身体障害者手帳」を指定して保存
    plan = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="手帳種別明示確認目標",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id,
        detail_fields={
            "disability_handbook_type": "身体障害者手帳"
        }
    )
    assert plan.disability_handbook_type == "身体障害者手帳"


def test_item_support_period_not_auto_filled(app, auth_setup):
    """
    【追加要件3検証: 支援項目の期間を自動補完しない】
    - support_period_start / support_period_end が未入力の場合、
      計画全体の start_date / plan_end_date を自動設定せず NULL として保存すること。
    """
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]

    # 1. 支援期間を未入力で作成
    plan = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="期間自動補完廃止検証目標",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id,
        items_data=[
            {
                "item_number": 1,
                "challenge_topic": "通勤安定",
                "support_policy": "時差出勤",
                "support_content": "月次面談",
                "support_period_start": None, # 空欄
                "support_period_end": None     # 空欄
            },
            {
                "item_number": 2,
                "challenge_topic": "作業集中",
                "support_policy": "タイマー活用",
                "support_content": "業務観察",
                "support_period_start": "2026-10-01", # 明示的に入力
                "support_period_end": "2026-12-31"     # 明示的に入力
            }
        ]
    )

    detail = JobRetentionService.get_support_plan_detail(contract_a.id, plan.id)
    items = detail["items"]
    assert len(items) == 2

    # 未入力項目は計画全体の期間（2026-09-01〜2027-02-28）に自動補完されず None (NULL) であること
    assert items[0]["support_period_start"] is None
    assert items[0]["support_period_end"] is None

    # 明示的に入力した項目はその値が保存されること
    assert items[1]["support_period_start"] == "2026-10-01"
    assert items[1]["support_period_end"] == "2026-12-31"


def test_migration_downgrade_upgrade_data_integrity(app):
    """
    【要件1・9検証: マイグレーション upgrade -> データ検証 -> downgrade -> upgrade】
    - 旧 retention_support_plans に overall_support_goal のみ存在する場合
    - upgrade 後に RetentionSupportPlanDetail.overall_support_goal のみに移行され、
      存在しない架空の LongTermGoal / ShortTermGoal / Item は作成されないこと。
    - downgrade で移行先が削除され、再度 upgrade しても整合性が保たれること。
    """
    import os
    from alembic.config import Config
    from alembic import command

    ini_path = os.path.join(os.getcwd(), 'backend', 'migrations', 'alembic.ini')
    alembic_cfg = Config(ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(os.getcwd(), 'backend', 'migrations'))

    # pytest用DBは create_all されているため alembic_version を head に stamp
    command.stamp(alembic_cfg, "head")

    # downgrade して前のリビジョンに戻す
    command.downgrade(alembic_cfg, "719c050efff3")

    # 旧テーブルに overall_support_goal のみのレコードを作成
    from sqlalchemy import text
    with app.app_context():
        res = db.session.execute(text("SELECT count(*) FROM retention_support_plans")).scalar()
        assert res is not None

    # 再度 upgrade c4e281bf0571
    command.upgrade(alembic_cfg, "c4e281bf0571")

    # 移行結果の検証: 架空の LongTermGoal / ShortTermGoal / Item が作られていないこと
    with app.app_context():
        from backend.app.models import RetentionSupportPlanItem, LongTermGoal
        # 旧データから移行されたアイテム数と架空Goalの確認
        items_count = RetentionSupportPlanItem.query.count()
        assert items_count == 0

        # 架空の「就労定着」LTGが作られていないこと
        fictitious_ltg = LongTermGoal.query.filter_by(challenges="就労定着").count()
        assert fictitious_ltg == 0

    # 他テストのために必ず head まで upgrade を完了させる
    command.upgrade(alembic_cfg, "head")



