# 🚨 修正点: 'from app...' を 'backend.app...' に修正
from backend.app.extensions import db
from backend.app.models import (
    User, UserPII, Supporter, RoleMaster, PermissionMaster,
    Corporation, ServiceCertificate, GrantedService, 
    ContractReportDetail, OfficeServiceConfiguration, OfficeSetting
)
from sqlalchemy.orm import joinedload
import os

# ====================================================================
# 1. 鍵取得ロジック（暗号化の土台）
# ====================================================================

def get_corporation_id_for_user(user: User) -> int:
    """
    利用者(User)から、その利用者が「在籍」している法人(Corporation)のIDを
    「契約」を辿って特定する。
    
    [論理チェーン]
    User -> ServiceCertificate -> GrantedService -> 
    ContractReportDetail -> OfficeServiceConfiguration -> 
    OfficeSetting -> Corporation
    """
    if not user:
        raise ValueError("User object is required to find corporation ID.")
        
    try:
        # Userに紐づく最新の有効な（または最も最近の）契約を辿る
        # 🚨 このクエリはシステムの「在籍」ロジックの核となる
        
        # 直近の受給者証を探す
        latest_cert = ServiceCertificate.query.filter_by(user_id=user.id)\
            .order_by(ServiceCertificate.certificate_issue_date.desc()).first()
            
        if not latest_cert:
            # 契約がない場合はデフォルト法人(ID:1)またはエラー
            # (初期登録時などを考慮し、暫定的に1を返す)
            return 1
            
        # 受給者証に紐づく支給決定を探す
        latest_grant = GrantedService.query.filter_by(certificate_id=latest_cert.id)\
            .order_by(GrantedService.granted_start_date.desc()).first()
            
        if not latest_grant:
            return 1
            
        # 支給決定に紐づく契約詳細を探す
        contract = ContractReportDetail.query.filter_by(granted_service_id=latest_grant.id).first()
        
        if not contract:
            return 1
            
        # 契約からサービス構成 -> 事業所 -> 法人 を辿る
        service_config = OfficeServiceConfiguration.query.get(contract.office_service_configuration_id)
        if service_config and service_config.office:
            return service_config.office.corporation_id
            
        return 1 # フォールバック

    except Exception as e:
        print(f"WARNING: Failed to resolve Corporation ID for User {user.id}: {e}")
        # 安全のためデフォルトまたはエラーを返す
        return 1


def get_corporation_kek(corporation_id: int) -> bytes:
    """
    【階層1】法人のマスターキー（KEK）を取得する。
    """
    # 🚨 暫定的な実装:
    # 本番環境では、KMSまたは安全なDBストアから法人IDに紐づくKEKを取得する。
    # 今回は環境変数から共通のKEKを取得してシミュレートする。
    temp_key = os.environ.get('FERNET_ENCRYPTION_KEY')
    if not temp_key:
        # 開発用デフォルトキー
        temp_key = b'gQfTq3-iJ4_1nZ-vY8-9jA_XyZ7_aB_C-dE_fG_hI_k='
        
    return temp_key if isinstance(temp_key, bytes) else temp_key.encode('utf-8')


def get_system_pii_key() -> bytes:
    """
    【階層2】システム共通鍵（DEK）を取得する。
    """
    key = os.environ.get('PII_ENCRYPTION_KEY')
    if not key:
        print("CRITICAL WARNING: PII_ENCRYPTION_KEY is not set. Using insecure default key.")
        key = b'bA-sTq-mG8_dK9-7_wN-xZ_yB_vC-1D-2E_fG_hI_j='
    return key if isinstance(key, bytes) else key.encode('utf-8')


# ====================================================================
# 2. 認証・権限サービス (Auth & RBAC)
# ====================================================================

def authenticate_supporter(email, password):
    """職員のログイン認証"""
    supporter = Supporter.query.filter_by(email=email).first()
    if supporter and supporter.check_password(password):
        return supporter
    return None

def check_permission(supporter_id, permission_name):
    """
    職員が特定の権限(Permission)を持っているか確認する。
    Supporter -> Roles -> Permissions の多対多リレーションを解決する。
    """
    supporter = Supporter.query.get(supporter_id)
    if not supporter:
        return False
    
    # 職員が持つ全てのロールから、権限セットを収集
    for role in supporter.roles:
        for perm in role.permissions:
            if perm.name == permission_name:
                return True
    
    return False