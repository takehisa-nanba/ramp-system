# backend/app/services/job_retention_service.py

import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.exc import IntegrityError
from backend.app.extensions import db
from backend.app.models import (
    JobRetentionContract, RetentionEmploymentEpisode,
    RetentionUserVoiceLog, RetentionEmployerFeedbackLog,
    RetentionSupportActionLog, MonthlyRetentionReport,
    RetentionSupportPlan,
    RetentionSupportPlanDetail, RetentionSupportPlanItem,
    RetentionSupportPlanSourceLink,
    SupportPlan, LongTermGoal, ShortTermGoal, ServiceCertificate,
    calculate_max_review_deadline, calculate_plan_end_date,
    compute_retention_deadline_status,
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

        contract_start_ym = contract.contract_start_date.strftime('%Y-%m') if contract.contract_start_date else None
        is_first_contract_month = (contract_start_ym == year_month)

        if prev_report and prev_report.status == 'FINALIZED' and prev_report.future_support_plan:
            support_goal_str = prev_report.future_support_plan
        elif is_first_contract_month:
            # 契約における「本当の初月」に限り、ACTIVE支援計画の大まかな支援目標を初期提案値とする
            active_plan = JobRetentionService.get_active_support_plan(contract_id)
            if active_plan and active_plan.overall_support_goal:
                support_goal_str = active_plan.overall_support_goal
            else:
                support_goal_str = ""
        else:
            # 通常月で前月FINALIZEDレポートや今後の支援内容がない場合は空欄とする（推測・フォールバック禁止）
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
    # 支援計画 (共通SupportPlan + 定着Detail + 様式2入力支援)
    # ====================================================================
    @staticmethod
    def get_active_support_plan(contract_id: int) -> Optional[RetentionSupportPlanDetail]:
        """現在有効(ACTIVE)な就労定着支援計画を取得（新構造: RetentionSupportPlanDetail + SupportPlan）"""
        return RetentionSupportPlanDetail.query.join(
            SupportPlan, RetentionSupportPlanDetail.support_plan_id == SupportPlan.id
        ).filter(
            RetentionSupportPlanDetail.retention_contract_id == contract_id,
            SupportPlan.plan_status == 'ACTIVE'
        ).order_by(SupportPlan.plan_version.desc()).first()

    @staticmethod
    def list_support_plans(contract_id: int) -> List[RetentionSupportPlanDetail]:
        """契約に紐づく就労定着支援計画の全版履歴を取得（新構造: 新しい版順）"""
        return RetentionSupportPlanDetail.query.join(
            SupportPlan, RetentionSupportPlanDetail.support_plan_id == SupportPlan.id
        ).filter(
            RetentionSupportPlanDetail.retention_contract_id == contract_id
        ).order_by(SupportPlan.plan_version.desc()).all()

    @staticmethod
    def get_support_plan_detail(contract_id: int, plan_id: int) -> Optional[Dict[str, Any]]:
        """厚労省様式2の全項目（基本情報スナップショット・支援内容①〜③・出所リンク等）を取得"""
        detail = RetentionSupportPlanDetail.query.filter_by(
            id=plan_id,
            retention_contract_id=contract_id
        ).first()

        if not detail:
            # support_plan_id での指定も許容
            detail = RetentionSupportPlanDetail.query.filter_by(
                support_plan_id=plan_id,
                retention_contract_id=contract_id
            ).first()

        if not detail:
            return None

        sp = detail.support_plan
        ltg = sp.long_term_goals[0] if sp.long_term_goals else None
        stg = ltg.short_term_goals[0] if (ltg and ltg.short_term_goals) else None

        status_info = detail.compute_deadline_status()

        items = []
        for it in detail.items:
            items.append({
                "id": it.id,
                "item_number": it.item_number,
                "short_term_goal_id": it.short_term_goal_id,
                "challenge_topic": it.challenge_topic,
                "support_policy": it.support_policy,
                "support_content": it.support_content,
                "support_period_start": it.support_period_start.isoformat() if it.support_period_start else None,
                "support_period_end": it.support_period_end.isoformat() if it.support_period_end else None,
                "support_frequency": it.support_frequency,
                "role_sharing": it.role_sharing,
                "implementation_status": it.implementation_status,
                "achievement_status": it.achievement_status,
                "effectiveness_satisfaction": it.effectiveness_satisfaction,
                "remaining_challenges": it.remaining_challenges
            })

        source_links = []
        for sl in detail.source_links:
            source_links.append({
                "id": sl.id,
                "plan_item_id": sl.plan_item_id,
                "target_field": sl.target_field,
                "source_type": sl.source_type,
                "source_id": sl.source_id,
                "excerpt_text": sl.excerpt_text
            })

        return {
            "id": detail.id,
            "support_plan_id": sp.id,
            "version": sp.plan_version,
            "status": sp.plan_status,
            "overall_support_goal": detail.overall_support_goal,
            "start_date": sp.plan_start_date.isoformat() if sp.plan_start_date else None,
            "plan_end_date": sp.plan_end_date.isoformat() if sp.plan_end_date else None,
            "next_plan_start_date": detail.next_plan_start_date.isoformat() if detail.next_plan_start_date else None,
            "next_review_deadline": detail.next_review_deadline.isoformat() if detail.next_review_deadline else None,
            "review_date": detail.review_date.isoformat() if detail.review_date else None,
            "review_reason": detail.review_reason,
            "deadline_status": status_info["status_code"],
            "days_diff": status_info["days_diff"],
            "is_overdue": status_info["is_overdue"],
            # 長期・短期目標 (共通Goalモデル - 架空フォールバック禁止)
            "long_term_goal": {
                "id": ltg.id,
                "description": ltg.description,
                "set_year_month": ltg.set_year_month,
                "target_year_month": ltg.target_year_month,
                "achievement_status": ltg.achievement_status
            } if ltg else None,
            "short_term_goal": {
                "id": stg.id,
                "description": stg.description,
                "set_year_month": stg.set_year_month,
                "target_year_month": stg.target_year_month,
                "achievement_status": stg.achievement_status
            } if stg else None,
            # 1. 利用者基本情報スナップショット
            "user_info": {
                "user_name": detail.user_name,
                "user_name_kana": detail.user_name_kana,
                "gender": detail.gender,
                "birth_date": detail.birth_date.isoformat() if detail.birth_date else None,
                "age_at_planning": detail.age_at_planning,
                "support_level": detail.support_level,
                "disability_handbook_type": detail.disability_handbook_type
            },
            # 2. 雇用先・職場環境・労働条件スナップショット
            "employment_info": {
                "employer_name": detail.employer_name,
                "employer_industry": detail.employer_industry,
                "employer_address": detail.employer_address,
                "employer_tel": detail.employer_tel,
                "employer_contact_person": detail.employer_contact_person,
                "job_start_date": detail.job_start_date.isoformat() if detail.job_start_date else None,
                "work_content": detail.work_content,
                "employment_type": detail.employment_type,
                "wage_condition": detail.wage_condition,
                "holiday_condition": detail.holiday_condition,
                "working_hours_and_break": detail.working_hours_and_break,
                "physical_work_environment": detail.physical_work_environment,
                "human_work_environment": detail.human_work_environment,
                "related_support_organizations": detail.related_support_organizations
            },
            # 3. 本人の状況・生活環境・定着課題
            "situation_info": {
                "pre_employment_handover": detail.pre_employment_handover,
                "user_wishes": detail.user_wishes,
                "health_condition": detail.health_condition,
                "living_environment_support": detail.living_environment_support,
                "retention_challenges": detail.retention_challenges
            },
            # 4. 本人説明・同意 & 事業所・スタッフ
            "office_and_staff_info": {
                "office_name": detail.office_name,
                "office_number": detail.office_number,
                "office_address": detail.office_address,
                "office_tel": detail.office_tel,
                "office_fax": detail.office_fax,
                "staff_creator_name": detail.staff_creator_name,
                "staff_evaluator_name": detail.staff_evaluator_name,
                "staff_manager_name": detail.staff_manager_name,
                "staff_service_manager_name": detail.staff_service_manager_name,
                "staff_job_supporter_name": detail.staff_job_supporter_name,
                "staff_explainer_name": detail.staff_explainer_name,
                "explained_date": detail.explained_date.isoformat() if detail.explained_date else None,
                "agreed_date": detail.agreed_date.isoformat() if detail.agreed_date else None,
                "consent_confirmed": detail.consent_confirmed,
                "consent_notes": detail.consent_notes,
                "evaluation_date": detail.evaluation_date.isoformat() if detail.evaluation_date else None,
                "overall_evaluation": detail.overall_evaluation,
                "special_notes": detail.special_notes
            },
            # 5. 内部整理情報
            "internal_info": {
                "internal_employer_wishes": detail.internal_employer_wishes,
                "internal_overall_policy": detail.internal_overall_policy
            },
            # 支援内容・評価テーブル (①〜③)
            "items": items,
            # 出所リンク (プロベナンス)
            "source_links": source_links
        }

    @staticmethod
    def get_plan_input_assistance_data(contract_id: int) -> Dict[str, Any]:
        """
        厚労省様式2計画書作成のための入力支援データを取得する。
        - 確定事実スナップショット（利用者基本情報・雇用先・事業所情報など）
          * 利用者情報: UserPII (氏名, ふりがな, 生年月日, 性別, 手帳) / ServiceCertificate (障害支援区分)
          * 固定文字列（「未設定」「未登録」「就労定着支援事業所」等）は返さず NULL/空 とする
          * 労働条件（雇用形態・賃金・休日・勤務時間）は自動設定せず、work_conditionsは参考情報として提供
        - 一次情報候補（本人の声・企業フィードバック・支援アクション・月次レポート）
        支援員が事実と判断を区別して計画書を作成できるように支援する。
        """
        contract = db.session.get(JobRetentionContract, contract_id)
        if not contract:
            raise ValueError("契約が見つかりません。")

        user = contract.user
        latest_ep = contract.episodes[-1] if contract.episodes else None
        office_config = contract.office_service_configuration
        office = office_config.office if office_config else None

        # 1. 利用者基本情報の確定事実候補 (UserPII & ServiceCertificate)
        user_name = None
        user_kana = None
        birth_d = None
        age_at_planning = None
        gender_str = None
        handbook_type = None
        support_level = None

        if user:
            user_name = user.display_name
            pii = getattr(user, 'pii', None)
            if pii:
                full_name = f"{pii.last_name or ''} {pii.first_name or ''}".strip()
                if full_name:
                    user_name = full_name
                full_kana = f"{pii.last_name_kana or ''} {pii.first_name_kana or ''}".strip()
                if full_kana:
                    user_kana = full_kana
                birth_d = pii.birth_date
                if birth_d:
                    today = datetime.date.today()
                    age_at_planning = today.year - birth_d.year - ((today.month, today.day) < (birth_d.month, birth_d.day))
                if pii.gender_legal:
                    gender_str = pii.gender_legal.name
                if pii.handbook_level:
                    handbook_type = pii.handbook_level

            # 障害支援区分: ServiceCertificate の最新証から取得
            if hasattr(user, 'certificates') and user.certificates:
                cert = user.certificates.order_by(ServiceCertificate.certificate_issue_date.desc()).first()
                if cert and cert.disability_support_classification:
                    support_level = cert.disability_support_classification

        # 2. 雇用先・労働条件の確定事実候補 (固定ダミー値は返さない)
        employer_name = latest_ep.workplace_name if latest_ep else None
        job_start_d = latest_ep.job_start_date if latest_ep else None
        job_title = latest_ep.job_title if latest_ep else None
        raw_work_conditions = latest_ep.work_conditions if latest_ep else None

        # 3. 事業所・スタッフ確定事実候補 (固定ダミー値は返さない)
        office_name = office.office_name if office else None
        office_number = office_config.jigyosho_bango if office_config and hasattr(office_config, 'jigyosho_bango') else None
        office_address = getattr(office, 'address', None) if office else None
        office_tel = getattr(office, 'phone_number', None) if office else None
        office_fax = getattr(office, 'fax_number', None) if office else None

        # 4. 一次情報からの候補リスト
        # 本人の声 (直近5件)
        voice_candidates = []
        for v in sorted(contract.voice_logs, key=lambda x: x.logged_at, reverse=True)[:5]:
            v_text = v.raw_voice or v.trouble_point or v.success_point or "（記録あり）"
            log_date_str = v.logged_at.strftime('%Y/%m/%d') if v.logged_at else ""
            voice_candidates.append({
                "id": v.id,
                "date": log_date_str,
                "topic": v.help_topic or "本人の声",
                "content": v_text,
                "source_type": "USER_VOICE",
                "label": f"[{log_date_str}] {v.help_topic or '本人の声'}: {v_text[:40]}..."
            })

        # 企業フィードバック (直近5件)
        feedback_candidates = []
        for fb in sorted(contract.employer_feedback_logs, key=lambda x: x.logged_at, reverse=True)[:5]:
            fb_text = fb.workplace_observation or fb.positive_changes or fb.consultation_topic or "（記録あり）"
            fb_date_str = fb.logged_at.strftime('%Y/%m/%d') if fb.logged_at else ""
            feedback_candidates.append({
                "id": fb.id,
                "date": fb_date_str,
                "topic": fb.consultation_topic or "企業フィードバック",
                "content": fb_text,
                "source_type": "EMPLOYER_FEEDBACK",
                "label": f"[{fb_date_str}] {fb.contact_person or '企業担当者'}: {fb_text[:40]}..."
            })

        # 支援アクション記録 (直近5件)
        action_candidates = []
        for act in sorted(contract.action_logs, key=lambda x: x.action_date, reverse=True)[:5]:
            action_candidates.append({
                "id": act.id,
                "date": act.action_date.isoformat(),
                "confirmed_situation": act.confirmed_situation,
                "provided_support": act.provided_support,
                "source_type": "SUPPORT_ACTION",
                "label": f"[{act.action_date.strftime('%Y/%m/%d')}] 状況: {act.confirmed_situation[:30]}... / 支援: {act.provided_support[:30]}..."
            })

        # 月次レポート (直近1件)
        latest_report = MonthlyRetentionReport.query.filter_by(
            contract_id=contract_id
        ).order_by(MonthlyRetentionReport.report_year_month.desc()).first()

        report_candidate = None
        if latest_report:
            report_candidate = {
                "id": latest_report.id,
                "report_year_month": latest_report.report_year_month,
                "support_goal": latest_report.support_goal,
                "support_content": latest_report.support_content,
                "future_support_plan": latest_report.future_support_plan,
                "stakeholder_efforts": latest_report.stakeholder_efforts,
                "sharing_notes": latest_report.sharing_notes,
                "source_type": "MONTHLY_REPORT"
            }

        # 現行ACTIVE計画（もしあれば次回見直し向けに参照）
        active_plan = JobRetentionService.get_active_support_plan(contract_id)
        current_plan_info = None
        if active_plan:
            current_plan_info = {
                "id": active_plan.id,
                "version": active_plan.version,
                "overall_support_goal": active_plan.overall_support_goal,
                "start_date": active_plan.start_date.isoformat() if active_plan.start_date else None,
                "plan_end_date": active_plan.plan_end_date.isoformat() if active_plan.plan_end_date else None
            }

        return {
            "contract_id": contract.id,
            "user_id": contract.user_id,
            "user_info_snapshot": {
                "user_name": user_name,
                "user_name_kana": user_kana,
                "gender": gender_str,
                "birth_date": birth_d.isoformat() if birth_d else None,
                "age_at_planning": age_at_planning,
                "support_level": support_level,
                "disability_handbook_type": handbook_type
            },
            "employment_info_snapshot": {
                "employer_name": employer_name,
                "employer_industry": None,
                "employer_address": None,
                "employer_tel": None,
                "employer_contact_person": None,
                "job_start_date": job_start_d.isoformat() if job_start_d else None,
                "work_content": job_title,
                "employment_type": None,
                "wage_condition": None, # work_conditionsを賃金欄へ自動設定しない
                "holiday_condition": None,
                "working_hours_and_break": None,
                "physical_work_environment": None,
                "human_work_environment": None,
                "related_support_organizations": None,
                "raw_work_conditions": raw_work_conditions # 参考候補として提示
            },
            "office_info_snapshot": {
                "office_name": office_name,
                "office_number": office_number,
                "office_address": office_address,
                "office_tel": office_tel,
                "office_fax": office_fax
            },
            "candidates": {
                "voice_candidates": voice_candidates,
                "feedback_candidates": feedback_candidates,
                "action_candidates": action_candidates,
                "latest_report": report_candidate,
                "work_conditions_candidate": raw_work_conditions
            },
            "current_plan": current_plan_info
        }

    @staticmethod
    def create_or_review_support_plan(
        contract_id: int,
        overall_support_goal: str,
        plan_end_date: Optional[datetime.date] = None,
        next_review_deadline: Optional[datetime.date] = None, # 後方互換用
        review_date: Optional[datetime.date] = None,
        review_reason: Optional[str] = None,
        start_date: Optional[datetime.date] = None,
        supporter_id: Optional[int] = None,
        items_data: Optional[List[Dict[str, Any]]] = None,
        source_links_data: Optional[List[Dict[str, Any]]] = None,
        detail_fields: Optional[Dict[str, Any]] = None,
        long_term_goal_data: Optional[Dict[str, Any]] = None,
        short_term_goal_data: Optional[Dict[str, Any]] = None
    ) -> RetentionSupportPlanDetail:
        """
        就労定着支援計画の新規作成または随時見直しを行う。
        共通個別支援計画基盤（SupportPlan, LongTermGoal, ShortTermGoal）と
        定着支援固有拡張（RetentionSupportPlanDetail, RetentionSupportPlanItem, SourceLink）
        を完全に統合して永続化する。

        - plan_end_date: 当該計画版の終了予定日 (原則: start_date + 6 calendar months - 1 day)
        - 初回作成時: plan_version=1, review_date=None, review_reason=None (初回策定は見直し理由ではない)
        - 見直し時:
            - 以前のACTIVE版をARCHIVEDに変更
            - 早期見直し時 (review_d <= 旧版終了予定日): 旧版の終了日を前日(review_d - 1日)として連続保持
            - 終了予定日後の遅延見直し: 旧版終了予定日+1日を新開始日として連続保持
            - plan_version=前版+1, 基準日は見直し日, 新計画終了予定日 <= 見直し日+6か月-1日
            - review_date / review_reason は RetentionSupportPlanDetail に保持
        - 架空目標・架空アイテムの自動生成を禁止（入力されたもののみ保存）
        - work_conditionsを賃金欄へ自動設定しない
        - 監査ログを記録
        """
        contract = db.session.get(JobRetentionContract, contract_id)
        if not contract:
            raise ValueError("契約が見つかりません。")

        if not overall_support_goal or not overall_support_goal.strip():
            raise ValueError("大まかな支援目標の入力は必須です。")

        # 終了予定日の取得（plan_end_date優先、後方互換でnext_review_deadlineも受付）
        target_end_date = plan_end_date or next_review_deadline

        active_detail = JobRetentionService.get_active_support_plan(contract_id)

        if not active_detail:
            # ========================
            # 初回作成
            # ========================
            # 初回策定時は review_date / review_reason を見直し情報として保存しない（初回は見直しではない）
            init_review_date = None
            init_review_reason = None

            base_date = start_date or contract.contract_start_date or datetime.date.today()
            max_allowed = calculate_plan_end_date(base_date)
            if target_end_date is None:
                target_end_date = max_allowed
            elif target_end_date > max_allowed:
                raise ValueError(
                    f"計画終了予定日は開始日（{base_date.strftime('%Y/%m/%d')}）から暦上の6か月以内（{max_allowed.strftime('%Y/%m/%d')}まで）に設定してください。"
                )
            if target_end_date < base_date:
                raise ValueError("計画終了予定日は開始日以降の日付を設定してください。")

            # 1. 共通親 SupportPlan 作成
            new_sp = SupportPlan(
                user_id=contract.user_id,
                plan_version=1,
                plan_status='ACTIVE',
                plan_start_date=base_date,
                plan_end_date=target_end_date,
                activated_at=base_date,
                office_service_configuration_id=contract.office_service_configuration_id,
                created_by_id=supporter_id
            )
            db.session.add(new_sp)
            db.session.flush()

            # 2. 共通 LongTermGoal 作成 (UIで支援員が確認・入力した値のみ保存、架空自動生成禁止)
            new_ltg = None
            if long_term_goal_data and long_term_goal_data.get('description'):
                ltg_desc = long_term_goal_data.get('description', '').strip()
                if ltg_desc:
                    new_ltg = LongTermGoal(
                        plan_id=new_sp.id,
                        description=ltg_desc,
                        challenges=long_term_goal_data.get('challenges'),
                        target_period_start=base_date,
                        target_period_end=target_end_date,
                        set_year_month=long_term_goal_data.get('set_year_month'),
                        target_year_month=long_term_goal_data.get('target_year_month'),
                        achievement_status=long_term_goal_data.get('achievement_status')
                    )
                    db.session.add(new_ltg)
                    db.session.flush()

            # 3. 共通 ShortTermGoal 作成 (UIで支援員が確認・入力した値のみ保存、架空自動生成禁止)
            new_stg = None
            if short_term_goal_data and short_term_goal_data.get('description') and new_ltg:
                stg_desc = short_term_goal_data.get('description', '').strip()
                if stg_desc:
                    new_stg = ShortTermGoal(
                        long_term_goal_id=new_ltg.id,
                        description=stg_desc,
                        target_period_start=base_date,
                        target_period_end=target_end_date,
                        next_review_date=target_end_date,
                        set_year_month=short_term_goal_data.get('set_year_month'),
                        target_year_month=short_term_goal_data.get('target_year_month'),
                        achievement_status=short_term_goal_data.get('achievement_status')
                    )
                    db.session.add(new_stg)
                    db.session.flush()

            # 4. 定着支援固有 Detail 作成
            detail_data = detail_fields.copy() if detail_fields else {}
            # 利用者名
            detail_data.setdefault('user_name', contract.user.display_name if contract.user else f"利用者#{contract.user_id}")
            latest_ep = contract.episodes[-1] if contract.episodes else None
            if latest_ep:
                detail_data.setdefault('employer_name', latest_ep.workplace_name)
                detail_data.setdefault('work_content', latest_ep.job_title)
                detail_data.setdefault('job_start_date', latest_ep.job_start_date)
                # work_conditions を wage_condition に自動代入しない (要件3)

            new_detail = RetentionSupportPlanDetail(
                support_plan_id=new_sp.id,
                retention_contract_id=contract_id,
                overall_support_goal=overall_support_goal.strip(),
                review_date=init_review_date, # 初回は None
                review_reason=init_review_reason, # 初回は None
                **{k: v for k, v in detail_data.items() if hasattr(RetentionSupportPlanDetail, k) and k not in ['id', 'support_plan_id', 'retention_contract_id', 'overall_support_goal', 'review_date', 'review_reason']}
            )
            db.session.add(new_detail)
            db.session.flush()

            # 5. RetentionSupportPlanItem 作成 (UI入力値のみ保存、架空デフォルト生成禁止)
            if items_data and len(items_data) > 0:
                for idx, it in enumerate(items_data):
                    item_rec = RetentionSupportPlanItem(
                        detail_id=new_detail.id,
                        short_term_goal_id=new_stg.id if new_stg else None,
                        item_number=it.get('item_number', idx + 1),
                        challenge_topic=it.get('challenge_topic'),
                        support_policy=it.get('support_policy'),
                        support_content=it.get('support_content'),
                        support_period_start=it.get('support_period_start', base_date),
                        support_period_end=it.get('support_period_end', target_end_date),
                        support_frequency=it.get('support_frequency'),
                        role_sharing=it.get('role_sharing'),
                        implementation_status=it.get('implementation_status'),
                        achievement_status=it.get('achievement_status'),
                        effectiveness_satisfaction=it.get('effectiveness_satisfaction'),
                        remaining_challenges=it.get('remaining_challenges')
                    )
                    db.session.add(item_rec)

            # 6. 一次情報出所追跡リンク作成
            if source_links_data:
                for sl in source_links_data:
                    link_rec = RetentionSupportPlanSourceLink(
                        detail_id=new_detail.id,
                        target_field=sl.get('target_field', 'overall_support_goal'),
                        source_type=sl.get('source_type', 'USER_VOICE'),
                        source_id=sl.get('source_id'),
                        excerpt_text=sl.get('excerpt_text')
                    )
                    db.session.add(link_rec)

            # 7. 第1段階 互換性担保: 旧 retention_support_plans にも同期書き込み
            old_compat_plan = RetentionSupportPlan(
                contract_id=contract_id,
                version=1,
                overall_support_goal=overall_support_goal.strip(),
                start_date=base_date,
                review_date=init_review_date, # 初回は None
                review_reason=init_review_reason, # 初回は None
                plan_end_date=target_end_date,
                status='ACTIVE',
                created_by_id=supporter_id
            )
            db.session.add(old_compat_plan)
            db.session.flush()

            # 監査ログ
            audit = AuditActionLog(
                actor_supporter_id=supporter_id,
                user_id=contract.user_id,
                action='CREATE_RETENTION_SUPPORT_PLAN',
                entity_type='SupportPlan',
                entity_id=new_sp.id,
                after_value=f"Version: 1, Goal: {overall_support_goal[:30]}, PlanEndDate: {target_end_date}",
                reason="就労定着支援計画（別紙様式2統合版）の新規作成"
            )
            db.session.add(audit)
            db.session.commit()
            return new_detail

        else:
            # ========================
            # 随時見直し（早期見直し・遅延見直し）
            # ========================
            old_sp = active_detail.support_plan
            old_end_date = old_sp.plan_end_date

            review_d = review_date or datetime.date.today()
            if not review_reason or not review_reason.strip():
                raise ValueError("計画見直し時は見直し理由の入力が必須です。")

            # 早期見直し vs 終了予定日後の遅延見直し
            if review_d <= old_end_date:
                # 早期見直し (終了予定日以前または当日)
                new_start_date = review_d
                adjusted_old_end = new_start_date - datetime.timedelta(days=1)
                old_sp.plan_end_date = adjusted_old_end
            else:
                # 終了予定日後の遅延見直し (旧版終了予定日の翌日を起点とし、期間の空白を作らない)
                new_start_date = old_end_date + datetime.timedelta(days=1)

            # 新版の標準 plan_end_date および6か月上限は new_start_date から計算
            max_allowed = calculate_plan_end_date(new_start_date)
            if target_end_date is None:
                target_end_date = max_allowed
            elif target_end_date > max_allowed:
                raise ValueError(
                    f"計画終了予定日は計画開始日（{new_start_date.strftime('%Y/%m/%d')}）から暦上の6か月以内（{max_allowed.strftime('%Y/%m/%d')}まで）に設定してください。"
                )
            if target_end_date < new_start_date:
                raise ValueError("計画終了予定日は計画開始日以降の日付を設定してください。")

            # 旧ACTIVE計画をアーカイブ
            old_sp.plan_status = 'ARCHIVED'
            db.session.flush()

            # 旧互換テーブルのACTIVEレコードもアーカイブ
            old_compat_active = RetentionSupportPlan.query.filter_by(
                contract_id=contract_id,
                status='ACTIVE'
            ).first()
            if old_compat_active:
                old_compat_active.status = 'ARCHIVED'
                if review_d <= old_end_date:
                    old_compat_active.plan_end_date = new_start_date - datetime.timedelta(days=1)
                db.session.flush()

            new_version = old_sp.plan_version + 1

            # 1. 共通親 SupportPlan 作成
            new_sp = SupportPlan(
                user_id=contract.user_id,
                plan_version=new_version,
                plan_status='ACTIVE',
                plan_start_date=new_start_date,
                plan_end_date=target_end_date,
                activated_at=new_start_date,
                office_service_configuration_id=contract.office_service_configuration_id,
                created_by_id=supporter_id,
                based_on_plan_id=old_sp.id
            )
            db.session.add(new_sp)
            db.session.flush()

            # 2. 共通 LongTermGoal 作成 (UI入力値のみ、架空生成禁止)
            new_ltg = None
            if long_term_goal_data and long_term_goal_data.get('description'):
                ltg_desc = long_term_goal_data.get('description', '').strip()
                if ltg_desc:
                    new_ltg = LongTermGoal(
                        plan_id=new_sp.id,
                        description=ltg_desc,
                        challenges=long_term_goal_data.get('challenges'),
                        target_period_start=new_start_date,
                        target_period_end=target_end_date,
                        set_year_month=long_term_goal_data.get('set_year_month'),
                        target_year_month=long_term_goal_data.get('target_year_month'),
                        achievement_status=long_term_goal_data.get('achievement_status')
                    )
                    db.session.add(new_ltg)
                    db.session.flush()

            # 3. 共通 ShortTermGoal 作成 (UI入力値のみ、架空生成禁止)
            new_stg = None
            if short_term_goal_data and short_term_goal_data.get('description') and new_ltg:
                stg_desc = short_term_goal_data.get('description', '').strip()
                if stg_desc:
                    new_stg = ShortTermGoal(
                        long_term_goal_id=new_ltg.id,
                        description=stg_desc,
                        target_period_start=new_start_date,
                        target_period_end=target_end_date,
                        next_review_date=target_end_date,
                        set_year_month=short_term_goal_data.get('set_year_month'),
                        target_year_month=short_term_goal_data.get('target_year_month'),
                        achievement_status=short_term_goal_data.get('achievement_status')
                    )
                    db.session.add(new_stg)
                    db.session.flush()

            # 4. 定着支援固有 Detail 作成
            detail_data = detail_fields.copy() if detail_fields else {}
            # 前版スナップショットを継承しつつ更新
            for col in [
                'user_name', 'user_name_kana', 'gender', 'birth_date', 'age_at_planning',
                'support_level', 'disability_handbook_type', 'employer_name', 'employer_industry',
                'employer_address', 'employer_tel', 'employer_contact_person', 'job_start_date',
                'work_content', 'employment_type', 'wage_condition', 'holiday_condition',
                'working_hours_and_break', 'physical_work_environment', 'human_work_environment',
                'related_support_organizations', 'pre_employment_handover', 'user_wishes',
                'health_condition', 'living_environment_support', 'retention_challenges',
                'office_name', 'office_number', 'office_address', 'office_tel', 'office_fax'
            ]:
                if col not in detail_data and hasattr(active_detail, col):
                    val = getattr(active_detail, col)
                    if val is not None:
                        detail_data[col] = val

            new_detail = RetentionSupportPlanDetail(
                support_plan_id=new_sp.id,
                retention_contract_id=contract_id,
                overall_support_goal=overall_support_goal.strip(),
                review_date=review_d, # 見直し時は review_d を保存
                review_reason=review_reason.strip(),
                **{k: v for k, v in detail_data.items() if hasattr(RetentionSupportPlanDetail, k) and k not in ['id', 'support_plan_id', 'retention_contract_id', 'overall_support_goal', 'review_date', 'review_reason']}
            )
            db.session.add(new_detail)
            db.session.flush()

            # 5. RetentionSupportPlanItem 作成 (UI入力値のみ、架空生成禁止)
            if items_data and len(items_data) > 0:
                for idx, it in enumerate(items_data):
                    item_rec = RetentionSupportPlanItem(
                        detail_id=new_detail.id,
                        short_term_goal_id=new_stg.id if new_stg else None,
                        item_number=it.get('item_number', idx + 1),
                        challenge_topic=it.get('challenge_topic'),
                        support_policy=it.get('support_policy'),
                        support_content=it.get('support_content'),
                        support_period_start=it.get('support_period_start', new_start_date),
                        support_period_end=it.get('support_period_end', target_end_date),
                        support_frequency=it.get('support_frequency'),
                        role_sharing=it.get('role_sharing'),
                        implementation_status=it.get('implementation_status'),
                        achievement_status=it.get('achievement_status'),
                        effectiveness_satisfaction=it.get('effectiveness_satisfaction'),
                        remaining_challenges=it.get('remaining_challenges')
                    )
                    db.session.add(item_rec)

            # 6. 一次情報出所追跡リンク作成
            if source_links_data:
                for sl in source_links_data:
                    link_rec = RetentionSupportPlanSourceLink(
                        detail_id=new_detail.id,
                        target_field=sl.get('target_field', 'overall_support_goal'),
                        source_type=sl.get('source_type', 'USER_VOICE'),
                        source_id=sl.get('source_id'),
                        excerpt_text=sl.get('excerpt_text')
                    )
                    db.session.add(link_rec)

            # 7. 第1段階 互換性担保: 旧 retention_support_plans にも同期書き込み
            old_compat_plan = RetentionSupportPlan(
                contract_id=contract_id,
                version=new_version,
                overall_support_goal=overall_support_goal.strip(),
                start_date=new_start_date,
                review_date=review_d,
                review_reason=review_reason.strip(),
                plan_end_date=target_end_date,
                status='ACTIVE',
                created_by_id=supporter_id
            )
            db.session.add(old_compat_plan)
            db.session.flush()

            # 監査ログ
            audit = AuditActionLog(
                actor_supporter_id=supporter_id,
                user_id=contract.user_id,
                action='REVIEW_RETENTION_SUPPORT_PLAN',
                entity_type='SupportPlan',
                entity_id=new_sp.id,
                after_value=f"Version: {new_version} (from {old_sp.plan_version}), Goal: {overall_support_goal[:30]}, PlanEndDate: {target_end_date}",
                reason=f"就労定着支援計画の随時見直し（理由: {review_reason.strip()[:50]}）"
            )
            db.session.add(audit)
            db.session.commit()
            return new_detail

