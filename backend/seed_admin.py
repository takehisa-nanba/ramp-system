import sys
import os
import datetime
from datetime import date

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app
from backend.app.extensions import db, bcrypt
from backend.app.models import (
    Supporter, SupporterPII, Corporation, OfficeSetting, 
    MunicipalityMaster, StaffActivityMaster, StatusMaster,
    User, UserPII, SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal,
    RoleMaster, PermissionMaster, JobTitleMaster, UserScheduleTemplate, UserDailySchedule
)


app = create_app()
with app.app_context():
    # 開発中のため、一度全て削除して再作成（スキーマ変更反映のため）
    # db.drop_all()
    # db.create_all()

    # 1. 権限マスターの整備
    permissions = [
        {'name': 'VIEW', 'desc': 'データの閲覧'},
        {'name': 'CREATE', 'desc': 'データの作成'},
        {'name': 'EDIT', 'desc': 'データの編集'},
        {'name': 'APPROVE', 'desc': 'データの承認'},
        {'name': 'DELETE', 'desc': 'データの削除'},
        {'name': 'VIEW_PII', 'desc': '個人情報の閲覧'},
        {'name': 'EDIT_PII', 'desc': '個人情報の編集'},
        {'name': 'EXPORT_PII', 'desc': '個人情報の出力'},
        {'name': 'VIEW_AUDIT_LOG', 'desc': '監査ログの閲覧'},
        {'name': 'VIEW_STAFF', 'desc': '職員情報の閲覧'},
        {'name': 'CREATE_STAFF', 'desc': '職員情報の登録'},
        {'name': 'EDIT_STAFF', 'desc': '職員情報の編集'},
    ]
    perm_objs = {}
    for p in permissions:
        obj = PermissionMaster.query.filter_by(name=p['name']).first()
        if not obj:
            obj = PermissionMaster(name=p['name'])
            db.session.add(obj)
        perm_objs[p['name']] = obj
    db.session.commit()

    # 福祉法令上の標準実務職種マスターの投入と権限設定
    job_titles_seed = [
        {
            'title_name': '管理者', 
            'is_management': True, 
            'is_qualified': False,
            'perms': ['VIEW', 'CREATE', 'EDIT', 'APPROVE', 'DELETE', 'VIEW_PII', 'EDIT_PII', 'VIEW_STAFF', 'CREATE_STAFF', 'EDIT_STAFF']
        },
        {
            'title_name': 'サービス管理責任者', 
            'is_management': False, 
            'is_qualified': True,
            'perms': ['VIEW', 'CREATE', 'EDIT', 'APPROVE', 'VIEW_PII', 'EDIT_PII', 'VIEW_STAFF']
        },
        {
            'title_name': '生活支援員', 
            'is_management': False, 
            'is_qualified': False,
            'perms': ['VIEW', 'CREATE', 'EDIT', 'VIEW_PII']
        },
        {
            'title_name': '職業指導員', 
            'is_management': False, 
            'is_qualified': False,
            'perms': ['VIEW', 'CREATE', 'EDIT', 'VIEW_PII']
        },
        {
            'title_name': '就労支援員', 
            'is_management': False, 
            'is_qualified': False,
            'perms': ['VIEW', 'CREATE', 'EDIT', 'VIEW_PII']
        },
        {
            'title_name': '事務員', 
            'is_management': False, 
            'is_qualified': False,
            'perms': ['VIEW', 'CREATE', 'EDIT', 'VIEW_PII']
        },
    ]
    for jt in job_titles_seed:
        title_obj = JobTitleMaster.query.filter_by(title_name=jt['title_name']).first()
        if not title_obj:
            title_obj = JobTitleMaster(
                title_name=jt['title_name'],
                is_management_role=jt['is_management'],
                is_qualified_role=jt['is_qualified']
            )
            db.session.add(title_obj)
        # 各職種に法令上・業務上の標準パーミッションをアタッチ（文字列ハードコード回避のため）
        title_obj.permissions = [perm_objs[pname] for pname in jt['perms'] if pname in perm_objs]
    db.session.commit()

    # 1-2. マスターデータの整備（自治体）
    municipality = MunicipalityMaster.query.filter_by(municipality_code='131016').first()
    if not municipality:
        municipality = MunicipalityMaster(municipality_code='131016', name='千代田区')
        db.session.add(municipality)

    # 活動タグ
    tags = [
        {'name': '個別支援・面談', 'is_direct': True},
        {'name': '送迎', 'is_direct': True},
        {'name': '企業実習同行', 'is_direct': True},
        {'name': '事務作業（記録・書類作成）', 'is_direct': False},
        {'name': '企業開拓・営業', 'is_direct': False},
        {'name': '会議・打ち合わせ', 'is_direct': False},
        {'name': '休憩', 'is_direct': False},
    ]
    for tag in tags:
        if not StaffActivityMaster.query.filter_by(activity_name=tag['name']).first():
            db.session.add(StaffActivityMaster(activity_name=tag['name'], is_direct_support=tag['is_direct']))

    statuses_to_seed = [
        {'name': '問い合わせ', 'description': '利用前の見込み客や問い合わせ段階', 'sort_order': 1},
        {'name': '利用中', 'description': '現在サービスを利用している状態', 'sort_order': 2},
        {'name': '利用終了（定着支援中）', 'description': '就職し、6か月の定着支援期間中', 'sort_order': 3},
        {'name': '利用終了（定着完了）', 'description': '6か月の定着支援が完了した状態', 'sort_order': 4},
        {'name': '利用終了（退所）', 'description': '就職以外の理由で利用を終了した状態', 'sort_order': 5},
    ]
    for s_data in statuses_to_seed:
        status = StatusMaster.query.filter_by(name=s_data['name']).first()
        if not status:
            db.session.add(StatusMaster(name=s_data['name'], description=s_data['description'], sort_order=s_data['sort_order']))
    
    db.session.commit()

    # 2. 法人・事業所
    corp = Corporation.query.filter_by(tenant_id='demo-tenant').first()
    if not corp:
        corp = Corporation(corporation_name='デモ法人株式会社', corporation_type='株式会社', tenant_id='demo-tenant')
        db.session.add(corp)
        db.session.commit()

    office = OfficeSetting.query.filter_by(office_name='デモ事業所').first()
    if not office:
        office = OfficeSetting(corporation_id=corp.id, office_name='デモ事業所', municipality_id=municipality.id)
        db.session.add(office)
        db.session.commit()
    
    # サービス種別と設定
    from backend.app.models import ServiceTypeMaster, OfficeServiceConfiguration
    
    services_to_seed = [
        {'name': '就労移行支援', 'service_code': 'TRANSITION', 'required_review_months': 6},
        {'name': '就労継続支援A型', 'service_code': 'CONTINUOUS_A', 'required_review_months': 6},
        {'name': '就労継続支援B型', 'service_code': 'CONTINUOUS_B', 'required_review_months': 6},
        {'name': '自立訓練（生活訓練）', 'service_code': 'TRAINING', 'required_review_months': 6},
        {'name': '就労定着支援', 'service_code': 'RETENTION', 'required_review_months': 6},
        {'name': '就労選択支援', 'service_code': 'SELECTION', 'required_review_months': 6},
    ]
    for s_info in services_to_seed:
        st = ServiceTypeMaster.query.filter_by(service_code=s_info['service_code']).first()
        if not st:
            db.session.add(ServiceTypeMaster(
                name=s_info['name'],
                service_code=s_info['service_code'],
                required_review_months=s_info['required_review_months']
            ))
    db.session.commit()
    
    service_type = ServiceTypeMaster.query.filter_by(service_code='TRANSITION').first()
    
    service_config = OfficeServiceConfiguration.query.filter_by(office_id=office.id).first()
    if not service_config:
        service_config = OfficeServiceConfiguration(
            office_id=office.id,
            service_type_master_id=service_type.id,
            jigyosho_bango='1310100001',
            capacity=20,
            initial_designation_date=date(2023, 4, 1)
        )
        db.session.add(service_config)
        db.session.commit()


    # 3. ロールの整備 (権限マスターはファイル上部で定義・登録済み)

    roles = [
        {'name': '法人管理者', 'scope': 'CORPORATE', 'is_admin': True, 'perms': 'ALL'},
        {'name': 'システム管理者', 'scope': 'SYSTEM', 'is_admin': True, 'perms': 'ALL'},
        {'name': '監査担当', 'scope': 'SYSTEM', 'is_admin': False, 'perms': ['VIEW', 'VIEW_AUDIT_LOG']},
    ]
    role_objs = []
    for r in roles:
        obj = RoleMaster.query.filter_by(name=r['name']).first()
        if not obj:
            obj = RoleMaster(name=r['name'], role_scope=r['scope'], is_admin=r['is_admin'])
            db.session.add(obj)
        else:
            obj.role_scope = r['scope']
            obj.is_admin = r['is_admin']
        
        # 既存・新規に関わらずパーミッション設定を同期する
        if r['perms'] == 'ALL':
            obj.permissions = list(perm_objs.values())
        else:
            obj.permissions = [perm_objs[pname] for pname in r['perms'] if pname in perm_objs]
        role_objs.append(obj)
    db.session.commit()

    # 4. 支援員 (Admin)
    pii = SupporterPII.query.filter_by(email='admin@example.com').first()
    if not pii:
      admin = Supporter(
          staff_code='admin-001', last_name='システム', first_name='管理者',
          last_name_kana='システム', first_name_kana='カンリシャ',
          hire_date=date.today(), employment_type='FULL_TIME',
          weekly_scheduled_minutes=2400, is_active=True, office_id=office.id
      )
      admin.roles = [r for r in role_objs if r.role_scope in ('SYSTEM', 'CORPORATE') and r.is_admin]
      db.session.add(admin)
      db.session.commit()

      # admin-001 に実務上の「管理者」職種をアタッチ
      admin_title = JobTitleMaster.query.filter_by(title_name='管理者').first()
      if admin_title and service_config:
          from backend.app.models import SupporterJobAssignment
          assignment = SupporterJobAssignment(
              supporter_id=admin.id,
              job_title_id=admin_title.id,
              office_service_configuration_id=service_config.id,
              start_date=date.today(),
              assigned_minutes=2400,
              is_deemed_assignment=False
          )
          db.session.add(assignment)
          db.session.commit()

      pii = SupporterPII(supporter_id=admin.id, email='admin@example.com')
      pii.set_password('password123')
      db.session.add(pii)
      db.session.commit()
    admin = Supporter.query.filter_by(staff_code='admin-001').first()

    # 4-2. 支援員 (セキュリティロールを持たない一般ユーザー) の追加
    pii_staff = SupporterPII.query.filter_by(email='staff@example.com').first()
    if not pii_staff:
        staff_user = Supporter(
            staff_code='staff-001', last_name='一般', first_name='支援員',
            last_name_kana='イッパン', first_name_kana='シエンイン',
            hire_date=date.today(), employment_type='FULL_TIME',
            weekly_scheduled_minutes=2400, is_active=True, office_id=office.id
        )
        db.session.add(staff_user)
        db.session.commit()
        
        # 職務として「生活支援員」を割り当てる
        staff_title = JobTitleMaster.query.filter_by(title_name='生活支援員').first()
        if staff_title and service_config:
            from backend.app.models import SupporterJobAssignment
            assignment = SupporterJobAssignment(
                supporter_id=staff_user.id,
                job_title_id=staff_title.id,
                office_service_configuration_id=service_config.id,
                start_date=date.today(),
                assigned_minutes=2400,
                is_deemed_assignment=False
            )
            db.session.add(assignment)
            db.session.commit()

        pii_staff = SupporterPII(supporter_id=staff_user.id, email='staff@example.com')
        pii_staff.set_password('password123')
        db.session.add(pii_staff)
        db.session.commit()


    # 3. 利用者データの作成 (佐藤 健太)
    active_status = StatusMaster.query.filter_by(name='利用中').first()
    user = User.query.filter_by(display_name='佐藤 健太').first()
    if not user:
        user = User(
            display_name='佐藤 健太',
            user_code='USR001', # ★ 追加: 利用者コード
            status_id=active_status.id,
            primary_supporter_id=admin.id,
            service_start_date=datetime.datetime.now().date()
        )
        db.session.add(user)
        db.session.flush()

        user_pii = UserPII(user_id=user.id)
        user_pii.last_name = "佐藤"
        user_pii.first_name = "健太"
        user_pii.email = "kenta.sato@example.com"
        user_pii.set_password("password123") # ★ パスワード設定
        db.session.add(user_pii)

        # 受給者証のシード追加
        from backend.app.models.core.service_certificate import ServiceCertificate, GrantedService
        
        cert = ServiceCertificate.query.filter_by(user_id=user.id).first()
        if not cert and service_config:
            cert = ServiceCertificate(
                user_id=user.id,
                office_service_configuration_id=service_config.id,
                certificate_issue_date=date(2024, 1, 1),
                municipality_master_id=municipality.id,
                certificate_type="受給者証",
                disability_support_classification="区分3"
            )
            db.session.add(cert)
            db.session.flush()
            
            # 支給上限を20日に設定してシード（超過テスト用）
            gs = GrantedService(
                certificate_id=cert.id,
                granted_start_date=date(2024, 1, 1),
                granted_end_date=date(2027, 12, 31),
                max_service_days=20,
                service_type_master_id=service_type.id
            )
            db.session.add(gs)
            db.session.commit()

    plan = SupportPlan.query.filter_by(user_id=user.id).first()
    if not plan:
        plan = SupportPlan(
            user_id=user.id, 
            plan_start_date=date(2024, 1, 1), 
            plan_end_date=date(2024, 12, 31), 
            plan_status='ACTIVE'
        )
        db.session.add(plan)
        db.session.commit()
        
    lt_goal = LongTermGoal.query.filter_by(plan_id=plan.id).first()
    if not lt_goal:
        lt_goal = LongTermGoal(
            plan_id=plan.id,
            description="就労に向けた基本的生活習慣の確立",
            target_period_start=date(2024, 1, 1),
            target_period_end=date(2024, 12, 31)
        )
        db.session.add(lt_goal)
        db.session.commit()

    st_goal = ShortTermGoal.query.filter_by(long_term_goal_id=lt_goal.id).first()
    if not st_goal:
        st_goal = ShortTermGoal(
            long_term_goal_id=lt_goal.id,
            description="毎朝9時に遅刻せず通所する",
            target_period_start=date(2024, 1, 1),
            target_period_end=date(2024, 6, 30),
            next_review_date=date(2024, 6, 30)
        )
        db.session.add(st_goal)
        db.session.commit()

    indiv_goal = IndividualSupportGoal.query.filter_by(short_term_goal_id=st_goal.id).first()
    if not indiv_goal:
        indiv_goal = IndividualSupportGoal(
            short_term_goal_id=st_goal.id,
            concrete_goal="朝の通所習慣化",
            user_commitment="目覚ましを2回かける",
            support_actions="通所時に笑顔で挨拶し、体調確認を行う",
            service_type="ON_SITE"
        )
        db.session.add(indiv_goal)
        db.session.commit()

    # === 利用者の追加 1: 鈴木 花子 (USR002) ===
    user2 = User.query.filter_by(display_name='鈴木 花子').first()
    if not user2:
        user2 = User(
            display_name='鈴木 花子',
            user_code='USR002',
            status_id=active_status.id,
            primary_supporter_id=admin.id,
            service_start_date=datetime.datetime.now().date()
        )
        db.session.add(user2)
        db.session.flush()

        user2_pii = UserPII(user_id=user2.id)
        user2_pii.last_name = "鈴木"
        user2_pii.first_name = "花子"
        user2_pii.email = "hanako.suzuki@example.com"
        user2_pii.set_password("password123")
        db.session.add(user2_pii)

        db.session.commit()

        # 鈴木花子の受給者証
        from backend.app.models.core.service_certificate import ServiceCertificate, GrantedService
        cert2 = ServiceCertificate(
            user_id=user2.id,
            office_service_configuration_id=service_config.id,
            certificate_issue_date=date(2024, 2, 1),
            municipality_master_id=municipality.id,
            certificate_type="受給者証",
            disability_support_classification="区分2"
        )
        db.session.add(cert2)
        db.session.flush()
        
        gs2 = GrantedService(
            certificate_id=cert2.id,
            granted_start_date=date(2024, 2, 1),
            granted_end_date=date(2027, 12, 31),
            max_service_days=23,
            service_type_master_id=service_type.id
        )
        db.session.add(gs2)
        db.session.commit()

        # 個別支援計画 (鈴木 花子)
        plan2 = SupportPlan(
            user_id=user2.id,
            plan_start_date=date(2024, 2, 1),
            plan_end_date=date(2025, 1, 31),
            plan_status='ACTIVE'
        )
        db.session.add(plan2)
        db.session.commit()

    # === 利用者の追加 2: 高橋 一郎 (USR003) ===
    user3 = User.query.filter_by(display_name='高橋 一郎').first()
    if not user3:
        user3 = User(
            display_name='高橋 一郎',
            user_code='USR003',
            status_id=active_status.id,
            primary_supporter_id=admin.id,
            service_start_date=datetime.datetime.now().date()
        )
        db.session.add(user3)
        db.session.flush()

        user3_pii = UserPII(user_id=user3.id)
        user3_pii.last_name = "高橋"
        user3_pii.first_name = "一郎"
        user3_pii.email = "ichiro.takahashi@example.com"
        user3_pii.set_password("password123")
        db.session.add(user3_pii)

        db.session.commit()

        # 高橋一郎の受給者証
        from backend.app.models.core.service_certificate import ServiceCertificate, GrantedService
        cert3 = ServiceCertificate(
            user_id=user3.id,
            office_service_configuration_id=service_config.id,
            certificate_issue_date=date(2024, 3, 1),
            municipality_master_id=municipality.id,
            certificate_type="受給者証",
            disability_support_classification="区分4"
        )
        db.session.add(cert3)
        db.session.flush()
        
        gs3 = GrantedService(
            certificate_id=cert3.id,
            granted_start_date=date(2024, 3, 1),
            granted_end_date=date(2027, 12, 31),
            max_service_days=23,
            service_type_master_id=service_type.id
        )
        db.session.add(gs3)
        db.session.commit()

        # 個別支援計画 (高橋 一郎)
        plan3 = SupportPlan(
            user_id=user3.id,
            plan_start_date=date(2024, 3, 1),
            plan_end_date=date(2025, 2, 28),
            plan_status='ACTIVE'
        )
        db.session.add(plan3)
        db.session.commit()

    # (来所実績シードは、予定の自動生成完了後に最後尾で行います)
    # 5. 予定テンプレートと日別予定のシード追加
    from backend.app.services.user_schedule_service import UserScheduleService
    from backend.app.utils.timezone import get_jst_today
    
    # ユーザーインスタンスを再ロードして NameError を防ぐ
    user = User.query.filter_by(display_name='佐藤 健太').first()
    user2 = User.query.filter_by(display_name='鈴木 花子').first()
    user3 = User.query.filter_by(display_name='高橋 一郎').first()
    
    all_users = [user, user2, user3]
    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    sched_service = UserScheduleService()
    
    for u in all_users:
        existing_tmpl = UserScheduleTemplate.query.filter_by(user_id=u.id).first()
        if not existing_tmpl:
            for day_name in days_list:
                is_sch = day_name not in ['Saturday', 'Sunday']
                db.session.add(UserScheduleTemplate(
                    user_id=u.id,
                    day_of_week=day_name,
                    is_scheduled=is_sch,
                    start_time='10:00' if is_sch else None,
                    end_time='16:00' if is_sch else None
                ))
            db.session.flush()
            
            # 実績が存在する2026年6月と、本日の日付の月に対して予定を自動生成
            sched_service.generate_daily_schedules_for_month(u.id, datetime.date(2026, 6, 1))
            sched_service.generate_daily_schedules_for_month(u.id, get_jst_today())

    # 6. 固定日付の打刻 (AttendanceRecord) と支援記録のシード追加
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    from backend.app.models import SupportRecord, UserDailyLog
    
    # 既存の打刻・日報・支援記録を一旦全削除
    AttendanceRecord.query.delete()
    SupportRecord.query.delete()
    UserDailyLog.query.delete()
    db.session.commit()
    
    dt_6_10 = datetime.datetime(2026, 6, 10)
    dt_6_11 = datetime.datetime(2026, 6, 11)
    
    # 佐藤 健太 (user_id=1) 
    # 6/10 打刻と支援記録あり（正常）
    db.session.add(AttendanceRecord(
        user_id=user.id,
        record_type='CHECK_IN',
        timestamp=dt_6_10.replace(hour=9, minute=55),
        location_data='GPS: 35.6812, 139.7671',
        is_confirmed=True
    ))
    db.session.add(AttendanceRecord(
        user_id=user.id,
        record_type='CHECK_OUT',
        timestamp=dt_6_10.replace(hour=16, minute=5),
        location_data='GPS: 35.6812, 139.7671',
        is_confirmed=True
    ))
    db.session.add(UserDailyLog(
        user_id=user.id,
        log_date=date(2026, 6, 10),
        location_type='ON_SITE',
        log_status='COMPLETED',
        support_content_notes='施設内での個別PC訓練実施。手順通りに作業が進められました。',
        morning_completed=True,
        evening_completed=True,
        auto_created=False
    ))
    db.session.add(SupportRecord(
        user_id=user.id,
        log_date=date(2026, 6, 10),
        supporter_id=admin.id,
        support_record_type='DIRECT_SUPPORT',
        support_content='[PC訓練] Excel基本操作の指導。意欲的に取り組まれていました。',
        observation_note='体調は良好。'
    ))
    
    # 6/11 CHECK_IN のみ（日報なし、支援記録なし＝退所打刻漏れ、支援記録漏れ警告発生）
    db.session.add(AttendanceRecord(
        user_id=user.id,
        record_type='CHECK_IN',
        timestamp=dt_6_11.replace(hour=10, minute=2),
        location_data='GPS: 35.6812, 139.7671',
        is_confirmed=True
    ))
    # 6/12 (金) は予定あり・打刻なし（無断欠席警告発生）
    
    # 鈴木 花子 (user_id=2)
    # 6/10 欠席申請が承認されてキャンセル済み (対応済み欠席、警告なし)
    # 鈴木花子の6/10予定をキャンセル状態に更新
    daily_hanako = UserDailySchedule.query.filter_by(user_id=user2.id, date=date(2026, 6, 10)).first()
    if daily_hanako:
        daily_hanako.is_scheduled = False
        daily_hanako.status = 'CANCELLED'
        daily_hanako.start_time = None
        daily_hanako.end_time = None
        
    db.session.add(SupportRecord(
        user_id=user2.id,
        log_date=date(2026, 6, 10),
        supporter_id=admin.id,
        support_record_type='ABSENCE_CONTACT',
        support_content='[欠席対応連絡] 欠席理由: 風邪のため自宅療養します。',
        decision_reason='本日お休みを了承しました。ゆっくり休むようお伝えしました。',
        observation_note='熱は37.5度とのこと。安否確認済み。'
    ))

    db.session.commit()

    print("Demo data seeded successfully.")
