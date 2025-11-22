import os
import sys
from dotenv import load_dotenv

# -------------------------------------------------------------------
# パス解決のロジック（重要）
# -------------------------------------------------------------------
# このスクリプトの場所: .../backend/scripts/seed.py
current_dir = os.path.dirname(os.path.abspath(__file__))

# backendフォルダ: .../backend
backend_dir = os.path.dirname(current_dir)

# プロジェクトルート: .../ramp-system (ここに .env がある)
project_root = os.path.dirname(backend_dir)

# 1. Pythonに 'backend' パッケージを認識させるため、ルートをパスに追加
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 2. ルートディレクトリにある .env を読み込む
dotenv_path = os.path.join(project_root, '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"🔧 Loaded environment variables from: {dotenv_path}")
else:
    print(f"⚠️ .env file not found at {dotenv_path}. Using default settings.")

# -------------------------------------------------------------------
# アプリケーションのインポート
# -------------------------------------------------------------------
from backend.app import create_app, db
from backend.app.models import (
    StatusMaster, DisabilityTypeMaster, GenderLegalMaster, MunicipalityMaster,
    JobTitleMaster, ServiceTypeMaster, QualificationMaster, SkillMaster,
    DocumentTypeMaster, CommitteeTypeMaster, StaffActivityMaster,
    RoleMaster, PermissionMaster, TrainingTypeMaster,
    FailureFactorMaster, IssueCategoryMaster
)

app = create_app()

def seed_masters():
    """
    システムの土台となるマスターデータを投入する。
    """
    # 接続先DBの確認（ここが postgresql://... になるはず）
    print(f"🌱 Seeding Master Data... (Target DB: {app.config['SQLALCHEMY_DATABASE_URI']})")

    # 1. ステータスマスタ
    statuses = [
        {'name': '相談・見学中', 'description': '正式契約前の見込み利用者', 'sort_order': 1},
        {'name': '利用中', 'description': '現在サービスを利用中', 'sort_order': 2},
        {'name': '休止中', 'description': '入院などで一時的に利用を中断', 'sort_order': 3},
        {'name': '定着支援中', 'description': '就職し、定着支援サービスを利用中', 'sort_order': 4},
        {'name': '移行後フォローアップ', 'description': '就職後6ヶ月以内の義務的支援期間', 'sort_order': 5},
        {'name': '利用終了', 'description': '退所（就職以外）', 'sort_order': 90},
        {'name': '利用終了（就職）', 'description': '就職による退所', 'sort_order': 91},
        {'name': '匿名化済', 'description': '個人情報が削除された状態', 'sort_order': 99},
    ]
    for s in statuses:
        if not StatusMaster.query.filter_by(name=s['name']).first():
            db.session.add(StatusMaster(**s))

    # 2. 障害種別マスタ
    disabilities = [
        {'name': '身体障害'}, {'name': '知的障害'}, {'name': '精神障害'},
        {'name': '発達障害'}, {'name': '難病等'}, {'name': '高次脳機能障害'},
    ]
    for d in disabilities:
        if not DisabilityTypeMaster.query.filter_by(name=d['name']).first():
            db.session.add(DisabilityTypeMaster(**d))

    # 3. 性別マスタ
    genders = [{'name': '男性'}, {'name': '女性'}]
    for g in genders:
        if not GenderLegalMaster.query.filter_by(name=g['name']).first():
            db.session.add(GenderLegalMaster(**g))

    # 4. 職務マスタ
    jobs = [
        {'title_name': '管理者', 'is_management_role': True, 'is_qualified_role': False},
        {'title_name': 'サービス管理責任者', 'is_management_role': False, 'is_qualified_role': True},
        {'title_name': '職業指導員', 'is_management_role': False, 'is_qualified_role': False},
        {'title_name': '生活支援員', 'is_management_role': False, 'is_qualified_role': False},
        {'title_name': '就労支援員', 'is_management_role': False, 'is_qualified_role': False},
        {'title_name': '目標工賃達成指導員', 'is_management_role': False, 'is_qualified_role': False},
    ]
    for j in jobs:
        if not JobTitleMaster.query.filter_by(title_name=j['title_name']).first():
            db.session.add(JobTitleMaster(**j))

    # 5. サービス種別マスタ
    services = [
        {'name': '就労移行支援', 'service_code': 'TRANSITION', 'required_review_months': 3},
        {'name': '就労継続支援A型', 'service_code': 'A_TYPE', 'required_review_months': 6},
        {'name': '就労継続支援B型', 'service_code': 'B_TYPE', 'required_review_months': 6},
        {'name': '就労定着支援', 'service_code': 'RETENTION', 'required_review_months': 6},
    ]
    for s in services:
        if not ServiceTypeMaster.query.filter_by(service_code=s['service_code']).first():
            db.session.add(ServiceTypeMaster(**s))

    # 6. 文書種別マスタ
    documents = [
        {'name': '履歴書', 'is_confidential': True},
        {'name': '職務経歴書', 'is_confidential': True},
        {'name': '障害者手帳', 'is_confidential': True},
        {'name': '受給者証（写）', 'is_confidential': True},
        {'name': '健康診断書', 'is_confidential': True},
        {'name': 'アセスメントシート', 'is_confidential': False},
        {'name': '同意書（共通）', 'is_confidential': True},
    ]
    for d in documents:
        if not DocumentTypeMaster.query.filter_by(name=d['name']).first():
            db.session.add(DocumentTypeMaster(**d))

    # 7. 委員会種別マスタ
    committees = [
        {'name': '虐待防止委員会', 'required_frequency_months': 12},
        {'name': '身体拘束適正化検討委員会', 'required_frequency_months': 12},
        {'name': '感染対策委員会', 'required_frequency_months': 3},
    ]
    for c in committees:
        if not CommitteeTypeMaster.query.filter_by(name=c['name']).first():
            db.session.add(CommitteeTypeMaster(**c))

    # 8. 研修・訓練種別マスタ
    trainings = [
        {'name': '虐待防止研修', 'required_frequency_months': 12},
        {'name': '身体拘束適正化研修', 'required_frequency_months': 12},
        {'name': '感染症対策研修', 'required_frequency_months': 12},
        {'name': 'プライバシー保護・倫理研修', 'required_frequency_months': 12},
        {'name': '避難消火訓練', 'required_frequency_months': 6},
        {'name': '自然災害（風水害）対策訓練', 'required_frequency_months': 12},
        {'name': '感染症発生時シミュレーション訓練', 'required_frequency_months': 12},
        {'name': '防犯訓練', 'required_frequency_months': 12},
    ]
    for t in trainings:
        if not TrainingTypeMaster.query.filter_by(name=t['name']).first():
            db.session.add(TrainingTypeMaster(**t))

    # 9. 職員活動種別マスタ
    activities = [
        {'activity_name': '個別支援（直接）'},
        {'activity_name': '個別支援（間接/記録）'},
        {'activity_name': '集団プログラム'},
        {'activity_name': '送迎'},
        {'activity_name': '企業開拓・営業'},
        {'activity_name': '会議・研修'},
        {'activity_name': '請求・事務作業'},
        {'activity_name': '休憩'},
    ]
    for a in activities:
        if not StaffActivityMaster.query.filter_by(activity_name=a['activity_name']).first():
            db.session.add(StaffActivityMaster(**a))

    # 10. 自治体マスタ
    municipalities = [
        {'municipality_code': '221309', 'name': '浜松市'},
        {'municipality_code': '222135', 'name': '磐田市'},
        {'municipality_code': '222160', 'name': '袋井市'},
        {'municipality_code': '222224', 'name': '湖西市'},
    ]
    for m in municipalities:
        if not MunicipalityMaster.query.filter_by(municipality_code=m['municipality_code']).first():
            db.session.add(MunicipalityMaster(**m))
            
    # 11. 失敗要因マスタ
    factors = [
        {'name': '個人因子', 'description': '体調、スキル、特性、心理状態など'},
        {'name': '環境因子', 'description': '設備、気温、騒音、道具の不備など'},
        {'name': '指導因子', 'description': '指示の曖昧さ、マニュアル不備、連携ミスなど'},
        {'name': '対人因子', 'description': '他利用者との関係、コミュニケーション齟齬など'},
    ]
    for f in factors:
        if not FailureFactorMaster.query.filter_by(name=f['name']).first():
            db.session.add(FailureFactorMaster(**f))

    # 12. 問題の所在マスタ
    issues = [
        {'name': '本人因子（特性・体調）'},
        {'name': '環境因子（物理・感覚）'},
        {'name': '対人関係（利用者間）'},
        {'name': '手順・マニュアル'},
        {'name': '家族・関係機関'},
        {'name': '職員連携'},
    ]
    for i in issues:
        if not IssueCategoryMaster.query.filter_by(name=i['name']).first():
            db.session.add(IssueCategoryMaster(**i))

    # 13. RBAC (Role & Permission)
    roles_data = [
        {
            'name': 'システム管理者', 
            'role_scope': 'SYSTEM', 
            'sort_order': 1,
            'perms': ['MANAGE_SYSTEM_SETTINGS', 'VIEW_DECRYPTED_PII', 'MANAGE_FINANCE', 'VIEW_ALL_RECORDS']
        },
        {
            'name': '法人代表者', 
            'role_scope': 'CORPORATE', 
            'sort_order': 2,
            'perms': ['VIEW_DECRYPTED_PII', 'MANAGE_FINANCE', 'VIEW_ALL_RECORDS']
        },
        {
            'name': '管理者', 
            'role_scope': 'JOB', 
            'sort_order': 3,
            'perms': ['APPROVE_DAILY_LOG', 'VIEW_ALL_RECORDS', 'CREATE_DAILY_LOG']
        },
        {
            'name': 'サービス管理責任者', 
            'role_scope': 'JOB', 
            'sort_order': 4,
            'perms': ['APPROVE_SUPPORT_PLAN', 'APPROVE_DAILY_LOG', 'VIEW_ALL_RECORDS', 'CREATE_DAILY_LOG']
        },
        {
            'name': '支援員', 
            'role_scope': 'JOB', 
            'sort_order': 5,
            'perms': ['CREATE_DAILY_LOG']
        },
    ]
    
    # 権限マスタの準備
    permissions = [
        'MANAGE_SYSTEM_SETTINGS', 'VIEW_DECRYPTED_PII', 'MANAGE_FINANCE', 
        'APPROVE_SUPPORT_PLAN', 'APPROVE_DAILY_LOG', 'CREATE_DAILY_LOG', 'VIEW_ALL_RECORDS'
    ]
    perm_objs = {}
    for p_name in permissions:
        perm = PermissionMaster.query.filter_by(name=p_name).first()
        if not perm:
            perm = PermissionMaster(name=p_name)
            db.session.add(perm)
            db.session.flush()
        perm_objs[p_name] = perm

    # ロールの作成と権限紐づけ
    for r_data in roles_data:
        role = RoleMaster.query.filter_by(name=r_data['name']).first()
        if not role:
            role = RoleMaster(name=r_data['name'], role_scope=r_data['role_scope'], sort_order=r_data['sort_order'])
            db.session.add(role)
            db.session.flush()
        
        role.permissions = []
        for p_name in r_data['perms']:
            if p_name in perm_objs:
                role.permissions.append(perm_objs[p_name])

    db.session.commit()
    print("✅ Master data seeded successfully!")

if __name__ == '__main__':
    with app.app_context():
        seed_masters()