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
    RoleMaster, PermissionMaster, JobTitleMaster
)


app = create_app()
with app.app_context():
    # 開発中のため、一度全て削除して再作成（スキーマ変更反映のため）
    # db.drop_all()
    # db.create_all()

    # 1. マスターデータの整備
    municipality = MunicipalityMaster.query.filter_by(municipality_code='131016').first()
    if not municipality:
        municipality = MunicipalityMaster(municipality_code='131016', name='千代田区')
        db.session.add(municipality)

    # 福祉法令上の標準実務職種マスターの投入
    job_titles_seed = [
        {'title_name': '管理者', 'is_management': True, 'is_qualified': False},
        {'title_name': 'サービス管理責任者', 'is_management': False, 'is_qualified': True},
        {'title_name': '生活支援員', 'is_management': False, 'is_qualified': False},
        {'title_name': '職業指導員', 'is_management': False, 'is_qualified': False},
        {'title_name': '就労支援員', 'is_management': False, 'is_qualified': False},
        {'title_name': '事務員', 'is_management': False, 'is_qualified': False},
    ]
    for jt in job_titles_seed:
        if not JobTitleMaster.query.filter_by(title_name=jt['title_name']).first():
            db.session.add(JobTitleMaster(
                title_name=jt['title_name'],
                is_management_role=jt['is_management'],
                is_qualified_role=jt['is_qualified']
            ))
    db.session.commit()

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


    # 3. 権限・ロールの整備
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

        # 個別支援計画 (高橋 一郎)
        plan3 = SupportPlan(
            user_id=user3.id,
            plan_start_date=date(2024, 3, 1),
            plan_end_date=date(2025, 2, 28),
            plan_status='ACTIVE'
        )
        db.session.add(plan3)
        db.session.commit()

    # 4. 来所実績 (AttendanceRecord) のシード追加
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    
    # 佐藤 健太 (user.id=1) の本日および昨日の来所実績
    att1 = AttendanceRecord.query.filter_by(user_id=1, record_type='CHECK_IN').first()
    if not att1:
        # 本日
        db.session.add(AttendanceRecord(
            user_id=1,
            record_type='CHECK_IN',
            timestamp=datetime.datetime.now(),
            location_data='GPS: 35.6812, 139.7671',
            is_confirmed=True
        ))
        # 昨日 (テスト用)
        db.session.add(AttendanceRecord(
            user_id=1,
            record_type='CHECK_IN',
            timestamp=datetime.datetime.now() - datetime.timedelta(days=1),
            location_data='GPS: 35.6812, 139.7671',
            is_confirmed=True
        ))
        
    # 高橋 一郎 (user3.id=3) の本日の来所実績
    att3 = AttendanceRecord.query.filter_by(user_id=user3.id, record_type='CHECK_IN').first()
    if not att3:
        db.session.add(AttendanceRecord(
            user_id=user3.id,
            record_type='CHECK_IN',
            timestamp=datetime.datetime.now(),
            location_data='GPS: 35.6812, 139.7671',
            is_confirmed=True
        ))
    db.session.commit()

    print("Demo data seeded successfully.")
