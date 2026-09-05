# backend/app/services/job_retention_service.py

import datetime
from typing import Dict, Any, List, Optional
from backend.app.extensions import db
from backend.app.models import (
    JobRetentionContract, RetentionEmploymentEpisode,
    RetentionUserVoiceLog, RetentionEmployerFeedbackLog,
    RetentionSupportActionLog, MonthlyRetentionReport,
    User, Supporter, AuditActionLog
)

class JobRetentionService:
    """就労定着支援ドメインの業務ロジック層"""

    @staticmethod
    def create_contract(
        user_id: int,
        office_service_configuration_id: Optional[int],
        contract_start_date: datetime.date,
        contract_end_date: datetime.date,
        is_company_involved: bool = False,
        consent_status: str = 'CONSENTED_ALL',
        initial_workplace_name: Optional[str] = None,
        job_start_date: Optional[datetime.date] = None,
        job_title: Optional[str] = None,
        work_conditions: Optional[str] = None,
        contract_details: Optional[str] = None,
        actor_supporter_id: Optional[int] = None
    ) -> JobRetentionContract:
        """定着支援契約を作成し、初期就労エピソードを登録する"""
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
        help_topic: Optional[str] = None
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
            help_topic=help_topic
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
        interview_records_str = "\n".join(interview_lines) if interview_lines else "当月面談記録なし"

        # 2. 企業訪問実施状況マッピング
        visit_lines = []
        for a in actions:
            if a.has_company_visit:
                visit_lines.append(f"・{a.action_date.strftime('%Y/%m/%d')} 企業訪問・職場状況把握")
        visit_records_str = "\n".join(visit_lines) if visit_lines else "当月企業訪問記録なし"

        # 3. 就労状況マッピング
        work_lines = []
        latest_ep = contract.episodes[-1] if contract.episodes else None
        if latest_ep:
            work_lines.append(f"【勤務先】{latest_ep.workplace_name} ({latest_ep.job_title or '一般就労'})")
        for a in actions:
            if a.confirmed_situation:
                work_lines.append(f"・[{a.action_date.strftime('%m/%d')}] {a.confirmed_situation}")
        work_status_str = "\n".join(work_lines) if work_lines else "特記すべき変化なし"

        # 4. 生活状況マッピング
        life_lines = []
        for v in voices:
            if v.trouble_point:
                life_lines.append(f"・困りごと: {v.trouble_point}")
        life_status_str = "\n".join(life_lines) if life_lines else "安定して生活を維持できている"

        # 5. 本人の状況・自力対処の状況・意向マッピング
        coping_lines = []
        for v in voices:
            voice_parts = []
            if v.raw_voice:
                voice_parts.append(f"「{v.raw_voice}」")
            if v.self_coping_action:
                voice_parts.append(f"本人の対処: {v.self_coping_action} (結果: {v.self_coping_result or '経過観察'})")
            if voice_parts:
                coping_lines.append(f"・[{v.logged_at.strftime('%m/%d')}] " + " / ".join(voice_parts))
        
        for a in actions:
            if a.user_action_observed:
                coping_lines.append(f"・[支援員観察 {a.action_date.strftime('%m/%d')}] {a.user_action_observed}")
        user_coping_str = "\n".join(coping_lines) if coping_lines else "本人からの特記事項なし"

        # 6. 企業の状況・評価・要望マッピング
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
        employer_feedback_str = "\n".join(employer_lines) if employer_lines else "企業からの相談・要望特になし"

        # 7. 今月実施した支援・調整内容マッピング
        support_lines = []
        for a in actions:
            parts = [f"・[{a.action_date.strftime('%m/%d')}] {a.provided_support}"]
            if a.staff_intervention_boundary:
                parts.append(f"(介在範囲: {a.staff_intervention_boundary})")
            support_lines.append(" ".join(parts))
        support_details_str = "\n".join(support_lines) if support_lines else "定期確認実施"

        # 8. 今後の支援方針・次回課題マッピング
        future_lines = []
        for a in actions:
            if a.next_step:
                future_lines.append(f"・{a.next_step}")
        future_policy_str = "\n".join(future_lines) if future_lines else "引き続き本人の自力対処を尊重し、必要な部分の伴走支援を継続する。"

        return {
            "contract_id": contract_id,
            "report_year_month": year_month,
            "interview_records": interview_records_str,
            "company_visit_records": visit_records_str,
            "work_status_summary": work_status_str,
            "life_status_summary": life_status_str,
            "user_coping_summary": user_coping_str,
            "employer_feedback_summary": employer_feedback_str,
            "support_details": support_details_str,
            "future_support_policy": future_policy_str,
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

        if not report:
            report = MonthlyRetentionReport(
                contract_id=contract_id,
                report_year_month=year_month,
                created_by_id=supporter_id
            )
            db.session.add(report)

        report.interview_records = report_data.get('interview_records')
        report.company_visit_records = report_data.get('company_visit_records')
        report.work_status_summary = report_data.get('work_status_summary')
        report.life_status_summary = report_data.get('life_status_summary')
        report.user_coping_summary = report_data.get('user_coping_summary')
        report.employer_feedback_summary = report_data.get('employer_feedback_summary')
        report.support_details = report_data.get('support_details')
        report.future_support_policy = report_data.get('future_support_policy')
        report.status = 'FINALIZED' if finalize else 'DRAFT'

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

    @staticmethod
    def get_monthly_report(contract_id: int, year_month: str) -> Optional[MonthlyRetentionReport]:
        return MonthlyRetentionReport.query.filter_by(
            contract_id=contract_id,
            report_year_month=year_month
        ).first()
