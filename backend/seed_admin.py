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
    RoleMaster, PermissionMaster
)


app = create_app()
with app.app_context():
    # 開発中のため、一度全て削除して再作成（スキーマ変更反映のため）
    db.drop_all()
    db.create_all()

    # 1. マスターデータの整備
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

    active_status = StatusMaster.query.filter_by(name='利用中').first()
    if not active_status:
        active_status = StatusMaster(name='利用中')
        db.session.add(active_status)
    
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
    service_type = ServiceTypeMaster.query.filter_by(service_code='TRANSITION').first()
    if not service_type:
        service_type = ServiceTypeMaster(name='就労移行支援', service_code='TRANSITION', required_review_months=6)
        db.session.add(service_type)
        db.session.commit()
    
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
        {'name': 'VIEW_PII', 'desc': '個人情報の閲覧'},
        {'name': 'EDIT_PII', 'desc': '個人情報の編集'},
        {'name': 'MANAGE_STAFF', 'desc': '職員の管理'},
        {'name': 'MANAGE_OFFICE', 'desc': '事業所の設定'},
        {'name': 'APPROVE_LOG', 'desc': '日報の承認'},
        {'name': 'EDIT_PLAN', 'desc': '支援計画の作成・編集'},
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
        {'name': '事業所管理者', 'scope': 'JOB'},
        {'name': '法人管理者', 'scope': 'CORPORATE'},
        {'name': 'システム管理者', 'scope': 'SYSTEM'},
    ]
    role_objs = []
    for r in roles:
        obj = RoleMaster.query.filter_by(name=r['name']).first()
        if not obj:
            obj = RoleMaster(name=r['name'], role_scope=r['scope'])
            # 全ての権限を付与
            obj.permissions = list(perm_objs.values())
            db.session.add(obj)
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
        # 全てのロールを付与 (最高権限)
        admin.roles = role_objs
        db.session.add(admin)
        db.session.commit()
        pii = SupporterPII(supporter_id=admin.id, email='admin@example.com')
        pii.set_password('password')
        db.session.add(pii)
        db.session.commit()


    # 3. 利用者データの作成 (佐藤 健太)
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
        user_pii.set_password("password") # ★ パスワード設定
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

    print("✅ 全てのデモデータの整合性を確認・補填しました。")
