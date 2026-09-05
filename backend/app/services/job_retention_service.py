# backend/app/services/job_retention_service.py

import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.exc import IntegrityError
from backend.app.extensions import db
from backend.app.models import (
    JobRetentionContract, RetentionEmploymentEpisode,
    RetentionUserVoiceLog, RetentionEmployerFeedbackLog,
    RetentionSupportActionLog, MonthlyRetentionReport,
    RetentionSupportPlan, calculate_max_review_deadline,
    User, Supporter, AuditActionLog
)

class JobRetentionConflictError(Exception):
    """就労定着支援でのリソース重複・競合例外"""
    pass

class JobRetentionService:
    """就労定着支援ドメインの業務ロジック層"""

    @staticmethod
    def create_contract(
        user_id: int,
        office_service_configuration_id: int,
        contract_start_date: datetime.date,
        contract_end_date: datetime.date,
        is_company_involved: bool = False,
        consent_status: str = 'NOT_SET',
        initial_workplace_name: Optional[str] = None,
        job_start_date: Optional[datetime.date] = None,
        job_title: Optional[str] = None,
        work_conditions: Optional[str] = None,
        contract_details: Optional[str] = None,
        actor_supporter_id: Optional[int] = None
    ) -> JobRetentionContract:
        """定着支援契約を作成し、初期就労エピソードを登録する"""
        if not office_service_configuration_id:
            raise ValueError("office_service_configuration_id は必須です。")

        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("利用者が見つかりません。")

        contract = JobRetentionContract(
            user_id=user_id,
            office_service_configuration_id=office_service_configuration_id,
            contract_start_date=contract_start_date,
            contract_end_date=contract_end_date,
            status='ACTIVE',
            is_company_involved=is_company_involved,
            consent_status=consent_status,
            contract_details=contract_details
        )
        db.session.add(contract)
        db.session.flush()

        if initial_workplace_name:
            episode = RetentionEmploymentEpisode(
                contract_id=contract.id,
                episode_number=1,
                workplace_name=initial_workplace_name,
                job_title=job_title,
                job_start_date=job_start_date or contract_start_date,
                work_conditions=work_conditions
            )
            db.session.add(episode)

        # 監査ログ
        audit = AuditActionLog(
            actor_supporter_id=actor_supporter_id,
            user_id=user_id,
            action='CREATE_RETENTION_CONTRACT',
            entity_type='JobRetentionContract',
            entity_id=contract.id,
            after_value=f"Start: {contract_start_date}, End: {contract_end_date}",
            reason="就労定着支援契約の開始"
        )
        db.session.add(audit)
        db.session.commit()
        return contract

    @staticmethod
    def list_contracts(office_service_config_id: Optional[int] = None, status: Optional[str] = None) -> List[JobRetentionContract]:
        """定着支援契約の一覧を取得"""
        query = JobRetentionContract.query
        if office_service_config_id:
            query = query.filter_by(office_service_configuration_id=office_service_config_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(JobRetentionContract.created_at.desc()).all()

    @staticmethod
    def get_contract(contract_id: int) -> Optional[JobRetentionContract]:
        """定着支援契約の詳細を取得"""
        return db.session.get(JobRetentionContract, contract_id)

    @staticmethod
    def get_contract_by_user(user_id: int) -> Optional[JobRetentionContract]:
        """利用者に紐づく有効な定着支援契約を取得"""
        return JobRetentionContract.query.filter_by(user_id=user_id, status='ACTIVE').first()

    @staticmethod
    def add_employment_episode(
        contract_id: int,
        workplace_name: str,
        job_start_date: datetime.date,
        job_title: Optional[str] = None,
        department_name: Optional[str] = None,
        work_conditions: Optional[str] = None,
        previous_episode_id: Optional[int] = None,
        actor_supporter_id: Optional[int] = None
    ) -> RetentionEmploymentEpisode:
        """転職時などに新しい就労エピソードを追加"""
        contract = db.session.get(JobRetentionContract, contract_id)
        if not contract:
            raise ValueError("契約が見つかりません。")

        count = len(contract.episodes)
        episode = RetentionEmploymentEpisode(
            contract_id=contract_id,
            episode_number=count + 1,
            workplace_name=workplace_name,
            job_title=job_title,
            department_name=department_name,
            job_start_date=job_start_date,
            work_conditions=work_conditions,
            previous_episode_id=previous_episode_id
        )
        # ステータスをACTIVEに復帰（TRANSITION_PENDINGだった場合）
        if contract.status == 'TRANSITION_PENDING':
            contract.status = 'ACTIVE'

        db.session.add(episode)
        db.session.flush()

        audit = AuditActionLog(
            actor_supporter_id=actor_supporter_id,
            user_id=contract.user_id,
            action='ADD_EMPLOYMENT_EPISODE',
            entity_type='RetentionEmploymentEpisode',
            entity_id=episode.id,
            after_value=f"Workplace: {workplace_name}, Start: {job_start_date}",
            reason="就労エピソードの追加"
        )
        db.session.add(audit)
        db.session.commit()
        return episode

    @staticmethod
    def end_employment_episode(
        episode_id: int,
        job_end_date: datetime.date,
        resignation_reason: Optional[str] = None,
        actor_supporter_id: Optional[int] = None
    ) -> RetentionEmploymentEpisode:
        """退職を記録（契約は自動終了させず、転職移行期間へ遷移）"""
        episode = db.session.get(RetentionEmploymentEpisode, episode_id)
        if not episode:
            raise ValueError("就労エピソードが見つかりません。")

        episode.job_end_date = job_end_date
        episode.resignation_reason = resignation_reason

        # 契約を即時終了せず、転職移行期間にする
        contract = episode.contract
        contract.status = 'TRANSITION_PENDING'

        audit = AuditActionLog(
            actor_supporter_id=actor_supporter_id,
            user_id=contract.user_id,
            action='END_EMPLOYMENT_EPISODE',
            entity_type='RetentionEmploymentEpisode',
            entity_id=episode.id,
            after_value=f"End Date: {job_end_date}, Reason: {resignation_reason}",
            reason="退職の記録（契約ステータス: TRANSITION_PENDING）"
        )
        db.session.add(audit)
        db.session.commit()
        return episode

    # ====================================================================
    # 一次情報ログ (本人の声)
    # ====================================================================
    @staticmethod
    def record_user_voice(
        contract_id: int,
        raw_voice: Optional[str] = None,
        trouble_point: Optional[str] = None,
        success_point: Optional[str] = None,
        self_coping_action: Optional[str] = None,
        self_coping_result: Optional[str] = None,
        needs_help: bool = False,
        help_topic: Optional[str] = None,
        input_channel: str = 'USER_DIRECT'
    ) -> RetentionUserVoiceLog:
        """本人がスマホ等から日記感覚で一次情報（できごと・対処）を登録"""
        contract = db.session.get(JobRetentionContract, contract_id)
        if not contract:
            raise ValueError("契約が見つかりません。")

        log = RetentionUserVoiceLog(
            contract_id=contract_id,
            raw_voice=raw_voice,
            trouble_point=trouble_point,
            success_point=success_point,
            self_coping_action=self_coping_action,
            self_coping_result=self_coping_result,
            needs_help=needs_help,
            help_topic=help_topic,
            input_channel=input_channel
        )
        db.session.add(log)
        db.session.commit()
        return log

    @staticmethod
    def list_user_voices(contract_id: int, limit: int = 50) -> List[RetentionUserVoiceLog]:
        return RetentionUserVoiceLog.query.filter_by(contract_id=contract_id).order_by(
            RetentionUserVoiceLog.logged_at.desc()
        ).limit(limit).all()

    # ====================================================================
    # 一次情報ログ (支援員の支援実施記録)
    # ====================================================================
    @staticmethod
    def record_support_action(
        contract_id: int,
        supporter_id: int,
        action_date: datetime.date,
        confirmed_situation: str,
        provided_support: str,
        has_user_interview: bool = False,
        interview_method: Optional[str] = None,
        has_company_visit: bool = False,
        has_coordination: bool = False,
        has_other_support: bool = False,
        user_action_observed: Optional[str] = None,
        staff_intervention_boundary: Optional[str] = None,
        next_step: Optional[str] = None
    ) -> RetentionSupportActionLog:
        """支援員による面談・訪問・調整等の実施記録（複数種別フラグを同時に保持可能）"""
        contract = db.session.get(JobRetentionContract, contract_id)
        if not contract:
            raise ValueError("契約が見つかりません。")

        action_log = RetentionSupportActionLog(
            contract_id=contract_id,
            supporter_id=supporter_id,
            action_date=action_date,
            has_user_interview=has_user_interview,
            interview_method=interview_method,
            has_company_visit=has_company_visit,
            has_coordination=has_coordination,
            has_other_support=has_other_support,
            confirmed_situation=confirmed_situation,
            provided_support=provided_support,
            user_action_observed=user_action_observed,
            staff_intervention_boundary=staff_intervention_boundary,
            next_step=next_step
        )
        db.session.add(action_log)
        db.session.flush()

        audit = AuditActionLog(
            actor_supporter_id=supporter_id,
            user_id=contract.user_id,
            action='RECORD_RETENTION_SUPPORT_ACTION',
            entity_type='RetentionSupportActionLog',
            entity_id=action_log.id,
            after_value=f"Date: {action_date}, Interview: {has_user_interview}, Visit: {has_company_visit}",
            reason="就労定着支援の実施記録登録"
        )
        db.session.add(audit)
        db.session.commit()
        return action_log

    @staticmethod
    def list_support_actions(contract_id: int) -> List[RetentionSupportActionLog]:
        return RetentionSupportActionLog.query.filter_by(contract_id=contract_id).order_by(
            RetentionSupportActionLog.action_date.desc()
        ).all()

    # ====================================================================
    # 支援レポート自動マッピング & 保存
    # ====================================================================
    @staticmethod
    def build_monthly_report_preview(contract_id: int, year_month: str) -> Dict[str, Any]:
        """
        一次情報をルールベースで公式就労定着支援レポートの各項目へマッピングした初期プレビューを構築する。
        一次情報（本人の声・支援記録・企業声）そのものは変更・上書きしない。
        """
        contract = db.session.get(JobRetentionContract, contract_id)
        if not contract:
            raise ValueError("契約が見つかりません。")

        try:
            year, month = map(int, year_month.split('-'))
            start_date = datetime.date(year, month, 1)
            # 月末日計算
            if month == 12:
                end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        except Exception:
            raise ValueError("年月フォーマットは 'YYYY-MM' である必要があります。")

        # 対象月の支援実施記録を取得
        actions = RetentionSupportActionLog.query.filter(
            RetentionSupportActionLog.contract_id == contract_id,
            RetentionSupportActionLog.action_date >= start_date,
            RetentionSupportActionLog.action_date <= end_date
        ).order_by(RetentionSupportActionLog.action_date.asc()).all()

        # 対象月の本人の声ログを取得
        voices = RetentionUserVoiceLog.query.filter(
            RetentionUserVoiceLog.contract_id == contract_id,
            RetentionUserVoiceLog.logged_at >= datetime.datetime.combine(start_date, datetime.time.min),
            RetentionUserVoiceLog.logged_at <= datetime.datetime.combine(end_date, datetime.time.max)
        ).order_by(RetentionUserVoiceLog.logged_at.asc()).all()

        # 対象月の企業フィードバックログを取得
        feedbacks = RetentionEmployerFeedbackLog.query.filter(
            RetentionEmployerFeedbackLog.contract_id == contract_id,
            RetentionEmployerFeedbackLog.logged_at >= datetime.datetime.combine(start_date, datetime.time.min),
            RetentionEmployerFeedbackLog.logged_at <= datetime.datetime.combine(end_date, datetime.time.max)
        ).order_by(RetentionEmployerFeedbackLog.logged_at.asc()).all()

        # 1. 面談実施状況マッピング
        interview_lines = []
        for a in actions:
            if a.has_user_interview:
                method_ja = {
                    'FACE_TO_FACE': '対面面談',
                    'ONLINE': 'オンライン面談',
                    'PHONE': '電話面談'
                }.get(a.interview_method, a.interview_method or '面談')
                interview_lines.append(f"・{a.action_date.strftime('%Y/%m/%d')} ({method_ja}) 担当: {a.supporter.last_name if a.supporter else ''}")
        interview_records_str = "\n".join(interview_lines) if interview_lines else ""

        # 2. 企業訪問実施状況マッピング
        visit_lines = []
        for a in actions:
            if a.has_company_visit:
                visit_lines.append(f"・{a.action_date.strftime('%Y/%m/%d')} 企業訪問・職場状況把握")
        visit_records_str = "\n".join(visit_lines) if visit_lines else ""

        # 3. 就労状況マッピング（一次情報のみ・推測補完禁止）
        work_lines = []
        latest_ep = contract.episodes[-1] if contract.episodes else None
        if latest_ep:
            title_part = f" ({latest_ep.job_title})" if latest_ep.job_title else ""
            work_lines.append(f"【勤務先】{latest_ep.workplace_name}{title_part}")
        for a in actions:
            if a.confirmed_situation:
                work_lines.append(f"・[{a.action_date.strftime('%m/%d')}] {a.confirmed_situation}")
        work_status_str = "\n".join(work_lines) if work_lines else ""

        # 4. 生活状況マッピング（一次情報のみ・推測補完禁止）
        life_lines = []
        for v in voices:
            if v.trouble_point:
                life_lines.append(f"・困りごと: {v.trouble_point}")
        life_status_str = "\n".join(life_lines) if life_lines else ""

        # 5. 本人の状況・自力対処の状況・意向マッピング（一次情報のみ・推測補完禁止）
        coping_lines = []
        for v in voices:
            voice_parts = []
            if v.raw_voice:
                voice_parts.append(f"「{v.raw_voice}」")
            if v.self_coping_action:
                result_part = f" (結果: {v.self_coping_result})" if v.self_coping_result else ""
                voice_parts.append(f"本人の対処: {v.self_coping_action}{result_part}")
            if voice_parts:
                coping_lines.append(f"・[{v.logged_at.strftime('%m/%d')}] " + " / ".join(voice_parts))
        
        for a in actions:
            if a.user_action_observed:
                coping_lines.append(f"・[支援員観察 {a.action_date.strftime('%m/%d')}] {a.user_action_observed}")
        user_coping_str = "\n".join(coping_lines) if coping_lines else ""

        # 6. 企業の状況・評価・要望マッピング（一次情報のみ・推測補完禁止）
        employer_lines = []
        for fb in feedbacks:
            parts = []
            if fb.workplace_observation:
                parts.append(f"職場様子: {fb.workplace_observation}")
            if fb.positive_changes:
                parts.append(f"良い変化: {fb.positive_changes}")
            if fb.direct_coordination_status:
                parts.append(f"本人調整: {fb.direct_coordination_status}")
            if parts:
                employer_lines.append(f"・[{fb.logged_at.strftime('%m/%d')}] " + " / ".join(parts))
        employer_feedback_str = "\n".join(employer_lines) if employer_lines else ""

        # 7. 今月実施した支援・調整内容マッピング（一次情報のみ・推測補完禁止）
        support_lines = []
        for a in actions:
            parts = [f"・[{a.action_date.strftime('%m/%d')}] {a.provided_support}"]
            if a.staff_intervention_boundary:
                parts.append(f"(介在範囲: {a.staff_intervention_boundary})")
            support_lines.append(" ".join(parts))
        support_details_str = "\n".join(support_lines) if support_lines else ""

        # 8. 今後の支援方針・次回課題マッピング（一次情報のみ・推測補完禁止）
        future_lines = []
        for a in actions:
            if a.next_step:
                future_lines.append(f"・{a.next_step}")
        future_policy_str = "\n".join(future_lines) if future_lines else ""

        # --- 公式帳票標準項目マッピング (出所関係を維持・推測補完禁止) ---
        # 1. 主な支援目標: 前月の確定済み(FINALIZED)レポートの今後の支援内容(future_support_plan)を初期値として引き継ぐ
        # 前月が存在しない初月や前月がDRAFTの場合は空欄とする（推測補完禁止）
        # 個別支援記録の next_step は当月の support_goal に直接使用せず、当月の future_support_plan の材料とする
        if month == 1:
            prev_year_month = f"{year - 1}-12"
        else:
            prev_year_month = f"{year}-{month - 1:02d}"

        prev_report = MonthlyRetentionReport.query.filter_by(
            contract_id=contract_id,
            report_year_month=prev_year_month
        ).first()

        if prev_report and prev_report.status == 'FINALIZED' and prev_report.future_support_plan:
            support_goal_str = prev_report.future_support_plan
        else:
            # 前月確定レポートが存在しない初月等の場合のみ、現在有効な支援計画の目標を初期提案値とする
            active_plan = JobRetentionService.get_active_support_plan(contract_id)
            if active_plan and active_plan.overall_support_goal:
                support_goal_str = active_plan.overall_support_goal
            else:
                support_goal_str = ""

        # 2. 支援実施内容: provided_supportと訪問/面談情報
        support_content_parts = []
        if interview_records_str:
            support_content_parts.append(f"【面談】\n{interview_records_str}")
        if visit_records_str:
            support_content_parts.append(f"【企業訪問】\n{visit_records_str}")
        if support_details_str:
            support_content_parts.append(f"【実施内容】\n{support_details_str}")
        support_content_str = "\n\n".join(support_content_parts) if support_content_parts else ""

        # 3. 支援結果: confirmed_situationや本人の対処結果
        result_lines = []
        for a in actions:
            if a.confirmed_situation:
                result_lines.append(f"・{a.action_date.strftime('%m/%d')}: {a.confirmed_situation}")
        for v in voices:
            if v.self_coping_result:
                result_lines.append(f"・本人の対処結果: {v.self_coping_result}")
        support_result_str = "\n".join(result_lines) if result_lines else ""

        # 4. 今後の支援内容: future_lines (個別支援記録の next_step を材料として反映)
        future_support_plan_str = "\n".join(future_lines) if future_lines else ""

        # 5. 対象者・事業主・関係機関等の取組: 本人の対処(voices)と企業の取組(feedbacks)
        stakeholder_parts = []
        if user_coping_str:
            stakeholder_parts.append(f"【本人の取組】\n{user_coping_str}")
        if employer_feedback_str:
            stakeholder_parts.append(f"【事業主・職場】\n{employer_feedback_str}")
        stakeholder_efforts_str = "\n\n".join(stakeholder_parts) if stakeholder_parts else ""

        # 6. 共有事項: 相談希望(voices.help_topic)や企業相談(feedbacks.consultation_topic)
        sharing_lines = []
        for v in voices:
            if v.needs_help and v.help_topic:
                sharing_lines.append(f"・本人相談希望: {v.help_topic}")
        for fb in feedbacks:
            if fb.consultation_topic:
                sharing_lines.append(f"・企業相談事項: {fb.consultation_topic}")
        sharing_notes_str = "\n".join(sharing_lines) if sharing_lines else ""

        return {
            "contract_id": contract_id,
            "report_year_month": year_month,
            # 内部整理項目
            "interview_records": interview_records_str,
            "company_visit_records": visit_records_str,
            "work_status_summary": work_status_str,
            "life_status_summary": life_status_str,
            "user_coping_summary": user_coping_str,
            "employer_feedback_summary": employer_feedback_str,
            "support_details": support_details_str,
            "future_support_policy": future_policy_str,
            # 公式帳票項目
            "support_goal": support_goal_str,
            "support_content": support_content_str,
            "support_result": support_result_str,
            "future_support_plan": future_support_plan_str,
            "stakeholder_efforts": stakeholder_efforts_str,
            "sharing_notes": sharing_notes_str,
            "status": "DRAFT"
        }

    @staticmethod
    def save_monthly_report(
        contract_id: int,
        supporter_id: int,
        year_month: str,
        report_data: Dict[str, Any],
        finalize: bool = False
    ) -> MonthlyRetentionReport:
        """月次支援レポートを保存または確定する"""
        contract = db.session.get(JobRetentionContract, contract_id)
        if not contract:
            raise ValueError("契約が見つかりません。")

        report = MonthlyRetentionReport.query.filter_by(
            contract_id=contract_id,
            report_year_month=year_month
        ).first()

        if report and report.status == 'FINALIZED':
            raise ValueError("確定済みの月次支援レポートは変更できません。")

        if not report:
            report = MonthlyRetentionReport(
                contract_id=contract_id,
                report_year_month=year_month,
                created_by_id=supporter_id
            )
            db.session.add(report)

        # 内部整理項目
        report.interview_records = report_data.get('interview_records')
        report.company_visit_records = report_data.get('company_visit_records')
        report.work_status_summary = report_data.get('work_status_summary')
        report.life_status_summary = report_data.get('life_status_summary')
        report.user_coping_summary = report_data.get('user_coping_summary')
        report.employer_feedback_summary = report_data.get('employer_feedback_summary')
        report.support_details = report_data.get('support_details')
        report.future_support_policy = report_data.get('future_support_policy')

        # 公式帳票標準項目
        report.support_goal = report_data.get('support_goal')
        report.support_content = report_data.get('support_content')
        report.support_result = report_data.get('support_result')
        report.future_support_plan = report_data.get('future_support_plan')
        report.stakeholder_efforts = report_data.get('stakeholder_efforts')
        report.sharing_notes = report_data.get('sharing_notes')

        report.status = 'FINALIZED' if finalize else 'DRAFT'

        try:
            # 監査ログ記録前に flush して実 entity_id を確定する
            db.session.flush()

            audit = AuditActionLog(
                actor_supporter_id=supporter_id,
                user_id=contract.user_id,
                action='FINALIZE_MONTHLY_RETENTION_REPORT' if finalize else 'SAVE_MONTHLY_RETENTION_REPORT',
                entity_type='MonthlyRetentionReport',
                entity_id=report.id,
                after_value=f"YearMonth: {year_month}, Status: {report.status}",
                reason=f"就労定着支援レポートの{'確定' if finalize else '下書き保存'}"
            )
            db.session.add(audit)
            db.session.commit()
            return report
        except IntegrityError as e:
            db.session.rollback()
            raise JobRetentionConflictError(
                f"契約ID {contract_id} の {year_month} レポートは既に存在するか、同時作成競合が発生しました。"
            ) from e

    @staticmethod
    def get_monthly_report(contract_id: int, year_month: str) -> Optional[MonthlyRetentionReport]:
        return MonthlyRetentionReport.query.filter_by(
            contract_id=contract_id,
            report_year_month=year_month
        ).first()

    # ====================================================================
    # 支援計画 (随時見直し & 6か月上限ガード & 版管理)
    # ====================================================================
    @staticmethod
    def get_active_support_plan(contract_id: int) -> Optional[RetentionSupportPlan]:
        """現在有効(ACTIVE)な支援計画を取得"""
        return RetentionSupportPlan.query.filter_by(
            contract_id=contract_id,
            status='ACTIVE'
        ).first()

    @staticmethod
    def list_support_plans(contract_id: int) -> List[RetentionSupportPlan]:
        """契約に紐づく支援計画の全版履歴を取得（新しい版順）"""
        return RetentionSupportPlan.query.filter_by(
            contract_id=contract_id
        ).order_by(RetentionSupportPlan.version.desc()).all()

    @staticmethod
    def create_or_review_support_plan(
        contract_id: int,
        overall_support_goal: str,
        next_review_deadline: datetime.date,
        review_date: Optional[datetime.date] = None,
        review_reason: Optional[str] = None,
        start_date: Optional[datetime.date] = None,
        supporter_id: Optional[int] = None
    ) -> RetentionSupportPlan:
        """
        支援計画の初回作成または随時見直しを行う。
        - 初回作成時: version=1, 基準日はstart_date (契約開始日等), 次回見直し期限 <= 基準日+6か月
        - 見直し時: 以前のACTIVE版をARCHIVEDに変更し、version=前版+1, 基準日は見直し日, 次回見直し期限 <= 見直し日+6か月
        - 監査ログを記録 (flush徹底)
        """
        contract = db.session.get(JobRetentionContract, contract_id)
        if not contract:
            raise ValueError("契約が見つかりません。")

        if not overall_support_goal or not overall_support_goal.strip():
            raise ValueError("大まかな支援目標の入力は必須です。")

        active_plan = JobRetentionService.get_active_support_plan(contract_id)

        if not active_plan:
            # 初回作成
            base_date = review_date or start_date or contract.contract_start_date or datetime.date.today()
            max_deadline = calculate_max_review_deadline(base_date)
            if next_review_deadline > max_deadline:
                raise ValueError(
                    f"次回見直し期限は基準日（{base_date.strftime('%Y/%m/%d')}）から暦上の6か月以内（{max_deadline.strftime('%Y/%m/%d')}まで）に設定してください。"
                )
            if next_review_deadline < base_date:
                raise ValueError("次回見直し期限は基準日以降の日付を設定してください。")

            new_plan = RetentionSupportPlan(
                contract_id=contract_id,
                version=1,
                overall_support_goal=overall_support_goal.strip(),
                start_date=base_date,
                review_date=review_date,
                review_reason=review_reason.strip() if review_reason else None,
                next_review_deadline=next_review_deadline,
                status='ACTIVE',
                created_by_id=supporter_id
            )
            db.session.add(new_plan)
            db.session.flush()

            audit = AuditActionLog(
                actor_supporter_id=supporter_id,
                user_id=contract.user_id,
                action='CREATE_RETENTION_SUPPORT_PLAN',
                entity_type='RetentionSupportPlan',
                entity_id=new_plan.id,
                after_value=f"Version: 1, Goal: {new_plan.overall_support_goal[:30]}, Deadline: {new_plan.next_review_deadline}",
                reason="就労定着支援計画の新規作成"
            )
            db.session.add(audit)
            db.session.commit()
            return new_plan
        else:
            # 随時見直し
            review_d = review_date or datetime.date.today()
            if not review_reason or not review_reason.strip():
                raise ValueError("計画見直し時は見直し理由の入力が必須です。")

            max_deadline = calculate_max_review_deadline(review_d)
            if next_review_deadline > max_deadline:
                raise ValueError(
                    f"次回見直し期限は見直し日（{review_d.strftime('%Y/%m/%d')}）から暦上の6か月以内（{max_deadline.strftime('%Y/%m/%d')}まで）に設定してください。"
                )
            if next_review_deadline < review_d:
                raise ValueError("次回見直し期限は見直し日以降の日付を設定してください。")

            # 旧ACTIVE計画をアーカイブ
            active_plan.status = 'ARCHIVED'
            db.session.flush()

            new_version = active_plan.version + 1
            new_plan = RetentionSupportPlan(
                contract_id=contract_id,
                version=new_version,
                overall_support_goal=overall_support_goal.strip(),
                start_date=review_d,
                review_date=review_d,
                review_reason=review_reason.strip(),
                next_review_deadline=next_review_deadline,
                status='ACTIVE',
                created_by_id=supporter_id
            )
            db.session.add(new_plan)
            db.session.flush()

            audit = AuditActionLog(
                actor_supporter_id=supporter_id,
                user_id=contract.user_id,
                action='REVIEW_RETENTION_SUPPORT_PLAN',
                entity_type='RetentionSupportPlan',
                entity_id=new_plan.id,
                after_value=f"Version: {new_version} (from {active_plan.version}), Goal: {new_plan.overall_support_goal[:30]}, Deadline: {new_plan.next_review_deadline}",
                reason=f"就労定着支援計画の随時見直し（理由: {review_reason.strip()[:50]}）"
            )
            db.session.add(audit)
            db.session.commit()
            return new_plan
