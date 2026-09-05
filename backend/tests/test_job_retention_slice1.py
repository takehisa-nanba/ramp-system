# backend/tests/test_job_retention_slice1.py

import pytest
import datetime
import uuid
from backend.app.extensions import db
from backend.app.models import (
    User, Supporter, StatusMaster, OfficeSetting, Corporation, MunicipalityMaster,
    ServiceTypeMaster, OfficeServiceConfiguration,
    JobRetentionContract, RetentionEmploymentEpisode,
    RetentionUserVoiceLog, RetentionSupportActionLog,
    MonthlyRetentionReport
)
from backend.app.services.job_retention_service import JobRetentionService

@pytest.fixture
def setup_data(app):
    with app.app_context():
        # 自治体マスタ
        muni = MunicipalityMaster.query.first()
        if not muni:
            muni = MunicipalityMaster(municipality_code="131016", name="東京都千代田区")
            db.session.add(muni)
            db.session.flush()

        # 法人
        corp = Corporation(corporation_name=f"テスト法人_{uuid.uuid4().hex[:4]}", corporation_type="株式会社")
        db.session.add(corp)
        db.session.flush()

        # 事業所
        office = OfficeSetting(
            office_name="テスト事業所",
            corporation_id=corp.id,
            municipality_id=muni.id,
            full_time_weekly_minutes=2400
        )
        db.session.add(office)
        db.session.flush()

        # サービス種別
        st = ServiceTypeMaster.query.first()
        if not st:
            st = ServiceTypeMaster(name="就労定着支援", service_code="RET")
            db.session.add(st)
            db.session.flush()

        # サービス設定
        osc = OfficeServiceConfiguration(
            office_id=office.id,
            service_type_master_id=st.id,
            jigyosho_bango=f"13{uuid.uuid4().hex[:8]}",
            capacity=20
        )
        db.session.add(osc)
        db.session.flush()

        # ステータスマスタ
        status = StatusMaster.query.filter_by(name='定着支援中').first()
        if not status:
            status = StatusMaster(name='定着支援中')
            db.session.add(status)
            db.session.flush()

        # 利用者
        user = User(
            display_name='山田 太郎',
            user_code=f'USER_RET_{uuid.uuid4().hex[:4]}',
            status_id=status.id
        )
        db.session.add(user)

        # 支援員
        supporter = Supporter(
            staff_code=f'STAFF_RET_{uuid.uuid4().hex[:4]}',
            first_name='花子',
            last_name='佐藤',
            first_name_kana='ハナコ',
            last_name_kana='サトウ',
            office_id=office.id,
            hire_date=datetime.date(2025, 4, 1),
            employment_type='FULL_TIME',
            weekly_scheduled_minutes=2400
        )
        db.session.add(supporter)
        db.session.commit()

        yield user, supporter, osc

def test_vertical_slice_1_full_flow(app, setup_data):
    """
    Vertical Slice 1: コア支援フローの貫通テスト
    定着支援開始 → 本人の声入力 → 複数支援種別の支援員記録 → レポート自動マッピング生成・保存
    """
    user, supporter, osc = setup_data
    with app.app_context():
        start_date = datetime.date(2026, 9, 1)
        end_date = datetime.date(2029, 8, 31)

        # 1. 契約作成（就労先エピソード含む）
        contract = JobRetentionService.create_contract(
            user_id=user.id,
            office_service_configuration_id=osc.id,
            contract_start_date=start_date,
            contract_end_date=end_date,
            is_company_involved=True,
            consent_status='NOT_SET', # 初期値は未同意
            initial_workplace_name='株式会社テクノロジーズ',
            job_start_date=start_date,
            job_title='事務補助・データ入力',
            actor_supporter_id=supporter.id
        )
        assert contract.id is not None
        assert contract.office_service_configuration_id == osc.id
        assert len(contract.episodes) == 1
        assert contract.episodes[0].workplace_name == '株式会社テクノロジーズ'

        # 2. 本人の声入力（一次情報・生の声）
        voice1 = JobRetentionService.record_user_voice(
            contract_id=contract.id,
            raw_voice='新しいExcel作業に少し戸惑ったけど、質問して進められた。',
            trouble_point='関数（VLOOKUP）の使い方がマニュアルと違って焦った。',
            success_point='隣の先輩に自分から声をかけて確認できた。',
            self_coping_action='深呼吸してマニュアルの更新日付を確認し、先輩に「今よろしいでしょうか」と聞いた。',
            self_coping_result='疑問が解消し、午後には予定通りの入力件数を達成できた。',
            needs_help=False,
            input_channel='USER_DIRECT'
        )
        assert voice1.id is not None
        assert voice1.input_channel == 'USER_DIRECT'

        # 3. 支援員の支援実施記録（複数支援種別フラグを保持）
        action1 = JobRetentionService.record_support_action(
            contract_id=contract.id,
            supporter_id=supporter.id,
            action_date=datetime.date(2026, 9, 15),
            has_user_interview=True,
            interview_method='FACE_TO_FACE',
            has_company_visit=True,
            has_coordination=True,
            confirmed_situation='業務の進捗状況は安定。周囲への質問もできており良好。',
            provided_support='上司との間で業務指示の出し方について調整を行い、優先順位を番号で明記するよう依頼した。',
            user_action_observed='不明点を自ら付箋にメモしてまとめて質問していた。',
            staff_intervention_boundary='企業側への配慮依頼の文言整理のみ支援員が介在し、日々の質問は本人が自力で行えている。',
            next_step='来月は業務量増加の予定があるため、疲れの蓄積がないか電話で中間確認予定。'
        )
        assert action1.id is not None
        assert action1.has_user_interview is True
        assert action1.has_company_visit is True
        assert action1.has_coordination is True

        # 4. 公式就労定着支援レポート各項目への自動マッピングプレビュー検証
        preview = JobRetentionService.build_monthly_report_preview(contract.id, '2026-09')
        assert preview['contract_id'] == contract.id
        assert preview['report_year_month'] == '2026-09'

        # 面談と企業訪問が正しく構造化抽出されているか
        assert '2026/09/15' in preview['interview_records']
        assert '対面面談' in preview['interview_records']
        assert '2026/09/15' in preview['company_visit_records']

        # 就労状況・本人の自力対処・支援内容が一次情報から抽出されているか
        assert '株式会社テクノロジーズ' in preview['work_status_summary']
        assert '深呼吸してマニュアルの更新日付を確認' in preview['user_coping_summary']
        assert '不明点を自ら付箋にメモ' in preview['user_coping_summary']
        assert '上司との間で業務指示の出し方' in preview['support_details']
        assert '本人が自力で行えている' in preview['support_details']

        # 公式帳票項目へのマッピング
        assert '上司との間で業務指示の出し方' in preview['support_content']
        assert '来月は業務量増加' in preview['future_support_plan']

        # 一次情報そのものは変更・上書きされていないこと
        v_check = db.session.get(RetentionUserVoiceLog, voice1.id)
        assert v_check.raw_voice == '新しいExcel作業に少し戸惑ったけど、質問して進められた。'

        # 5. 月次レポートの確定保存
        report = JobRetentionService.save_monthly_report(
            contract_id=contract.id,
            supporter_id=supporter.id,
            year_month='2026-09',
            report_data=preview,
            finalize=True
        )
        assert report.id is not None
        assert report.status == 'FINALIZED'
        assert report.report_year_month == '2026-09'

        # 6. 退職時の自動終了防止・TRANSITION_PENDING遷移検証
        episode = contract.episodes[0]
        end_ep = JobRetentionService.end_employment_episode(
            episode_id=episode.id,
            job_end_date=datetime.date(2026, 9, 30),
            resignation_reason='契約満了に伴うキャリアアップ転職準備',
            actor_supporter_id=supporter.id
        )
        # 契約が自動終了(TERMINATED)されず、TRANSITION_PENDINGになっていること
        c_check = db.session.get(JobRetentionContract, contract.id)
        assert c_check.status == 'TRANSITION_PENDING'
        assert end_ep.job_end_date == datetime.date(2026, 9, 30)
