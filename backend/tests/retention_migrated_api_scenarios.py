"""Real HTTP update flows using synthetic users in the migrated disposable DB."""
from datetime import date

from flask_jwt_extended import create_access_token


def exercise_update_api(app, ids):
    from backend.app import db
    from backend.app.models import (JobTitleMaster, SupporterJobAssignment,
                                    SupportPlan, JobRetentionContract, SupportRecord)
    user_id, staff_id, config_id = ids
    with app.app_context():
        title = JobTitleMaster.query.filter_by(title_name='サービス管理責任者').first()
        if title is None:
            title = JobTitleMaster(title_name='サービス管理責任者', is_qualified_role=True)
            db.session.add(title)
            db.session.flush()
        db.session.add(SupporterJobAssignment(supporter_id=staff_id, job_title_id=title.id,
            office_service_configuration_id=config_id, start_date=date(2020, 1, 1), assigned_minutes=2400))
        db.session.commit()
        headers = {'Authorization': 'Bearer ' + create_access_token(identity=f'staff:{staff_id}')}
    client = app.test_client()
    results = []

    def call(method, path, payload, expected, label):
        response = getattr(client, method)(path, json=payload, headers=headers)
        assert response.status_code == expected, label + ': HTTP ' + str(response.status_code)
        results.append(label)
        return response.get_json()

    contract = call('post', f'/api/job-retention/users/{user_id}/start', {
        'office_service_configuration_id': config_id, 'contract_start_date': '2026-09-30',
        'contract_end_date': '2027-09-29', 'reason': 'validation'}, 201, 'api_start')
    contract_id = contract['id']
    plan = call('post', '/api/plans/', {'user_id': user_id,
        'office_service_configuration_id': config_id, 'plan_start_date': '2026-09-30',
        'plan_end_date': '2027-09-29'}, 201, 'api_plan_draft')
    plan_id = plan['plan_id']
    call('put', f'/api/plans/{plan_id}', {'plan_start_date': '2026-09-29'}, 400,
         'api_plan_outside_contract_rejected')
    call('put', f'/api/plans/{plan_id}', {'plan_start_date': '2026-09-30',
         'plan_end_date': '2027-09-29'}, 200, 'api_plan_period_update')
    call('put', f'/api/plans/{plan_id}/goals', {'long_term_goals': [{
        'description': 'validation', 'challenges': 'validation', 'short_term_goals': []}]},
         200, 'api_plan_goals')
    call('post', '/api/case-conferences', {'user_id': user_id, 'support_plan_id': plan_id,
        'conference_type': 'PERSON_CENTERED_MEETING', 'concern_summary': 'validation',
        'agreed_action': 'validation', 'user_participated': True, 'participant_ids': [staff_id],
        'conference_datetime': '2026-10-01T10:00:00'}, 201, 'api_case_conference_create')
    call('post', f'/api/plans/{plan_id}/approve', {}, 200, 'api_plan_approve')
    consent = call('post', f'/api/plans/{plan_id}/consent', {'user_id': user_id,
        'consent_proof': 'DIGITAL_SIGNATURE'}, 201, 'api_consent_insert_legacy_columns_nullable')
    call('post', f'/api/plans/{plan_id}/activate', {'consent_log_id': consent['consent_log_id']},
         200, 'api_plan_activate')
    record = {'user_id': user_id, 'office_service_configuration_id': config_id,
              'support_plan_id': plan_id, 'log_date': '2026-10-01',
              'support_content': 'validation', 'support_duration_seconds': 60}
    call('post', '/api/records', record, 201, 'api_retention_support_record')
    call('post', '/api/records', dict(record, log_date='2026-09-29'), 400,
         'api_record_outside_period_rejected')
    monitoring = call('post', '/api/monitoring-reports', {'support_plan_id': plan_id,
        'report_date': '2026-10-01', 'monitoring_summary': 'validation'}, 201, 'api_monitoring_create')
    call('post', f"/api/monitoring-reports/{monitoring['id']}/complete", {}, 200,
         'api_monitoring_complete')
    # Keep a pending plan at finish, then prove it cannot be activated.
    with app.app_context():
        pending = SupportPlan(user_id=user_id, office_service_configuration_id=config_id,
            plan_status='PENDING_CONSENT', plan_start_date=date(2026, 9, 30), plan_end_date=date(2027, 9, 29))
        db.session.add(pending)
        db.session.commit()
        pending_id = pending.id
    pending_consent = call('post', f'/api/plans/{pending_id}/consent', {'user_id': user_id},
                           201, 'api_pending_consent')
    call('post', f'/api/job-retention/contracts/{contract_id}/finish', {
        'contract_end_date': '2026-10-01', 'reason': 'validation'}, 200, 'api_finish')
    call('post', f'/api/plans/{pending_id}/activate', {
        'consent_log_id': pending_consent['consent_log_id']}, 400, 'api_activate_after_finish_rejected')
    call('post', '/api/records', record, 400, 'api_archived_plan_record_rejected')
    with app.app_context():
        assert db.session.get(JobRetentionContract, contract_id).status == 'FINISHED'
        assert db.session.get(SupportPlan, plan_id).plan_status == 'ARCHIVED'
        assert db.session.get(SupportPlan, plan_id).plan_end_date == date(2027, 9, 29)
        assert db.session.get(SupportPlan, pending_id).plan_status == 'PENDING_CONSENT'
        assert SupportRecord.query.filter_by(user_id=user_id).count() == 1
    results.append('api_finish_preserves_signed_dates_and_pending_plan')
    return results
