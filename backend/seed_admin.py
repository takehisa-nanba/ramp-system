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
    User, UserPII, SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal
)

app = create_app()
with app.app_context():
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

    # 3. 支援員 (Admin)
    pii = SupporterPII.query.filter_by(email='admin@example.com').first()
    if not pii:
        admin = Supporter(
            staff_code='admin-001', last_name='システム', first_name='管理者',
            last_name_kana='システム', first_name_kana='カンリシャ',
            hire_date=date.today(), employment_type='FULL_TIME',
            weekly_scheduled_minutes=2400, is_active=True, office_id=office.id
        )
        db.session.add(admin)
        db.session.commit()
        pii = SupporterPII(supporter_id=admin.id, email='admin@example.com')
        pii.set_password('password')
        db.session.add(pii)
        db.session.commit()

    # 4. 利用者・支援計画
    user = User.query.filter_by(display_name='佐藤 健太').first()
    if not user:
        user = User(display_name='佐藤 健太', status_id=active_status.id)
        db.session.add(user)
        db.session.commit()
        
        user_pii = UserPII(user_id=user.id, birth_date=date(1990, 5, 15), email='sato@example.com')
        user_pii.last_name = '佐藤'
        user_pii.first_name = '健太'
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
