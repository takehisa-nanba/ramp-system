# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
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
    """
    if not user:
        # ユーザーオブジェクトがない場合はデフォルトIDを返す（またはエラー）
        return 1
        
    try:
        # 1. 直近の受給者証を探す
        latest_cert = ServiceCertificate.query.filter_by(user_id=user.id)\
            .order_by(ServiceCertificate.certificate_issue_date.desc()).first()
            
        if not latest_cert:
            return 1 # 契約がない場合（デフォルト）
            
        # 2. 受給者証に紐づく最新の支給決定を探す
        latest_grant = GrantedService.query.filter_by(certificate_id=latest_cert.id)\
            .order_by(GrantedService.granted_start_date.desc()).first()
            
        if not latest_grant:
            return 1
            
        # 3. 支給決定に紐づく契約詳細を探す
        # ★ ここで変数名 'contract' を定義する
        contract = ContractReportDetail.query.filter_by(granted_service_id=latest_grant.id).first()
        
        if not contract:
            return 1
            
        # 4. 契約からサービス構成 -> 事業所 -> 法人 を辿る
        # (SQLAlchemy 2.0 style: db.session.get)
        service_config = db.session.get(OfficeServiceConfiguration, contract.office_service_configuration_id)
        
        if not service_config:
            return 1

        office = db.session.get(OfficeSetting, service_config.office_id)
        
        if office:
            return office.corporation_id
            
        return 1 # フォールバック

    except Exception as e:
        print(f"WARNING: Failed to resolve Corporation ID for User {user.id}: {e}")
        return 1


def get_corporation_kek(corporation_id: int) -> bytes:
    """
    【階層1】法人のマスターキー（KEK）を取得する。
    """
    # 🚨 暫定的な実装: 環境変数から共通キーを取得
    temp_key = os.environ.get('FERNET_ENCRYPTION_KEY')
    if not temp_key:
        # 開発用デフォルトキー (Base64 encoded 32 bytes)
        temp_key = b'gQfTq3-iJ4_1nZ-vY8-9jA_XyZ7_aB_C-dE_fG_hI_k='
        
    return temp_key if isinstance(temp_key, bytes) else temp_key.encode('utf-8')


def get_system_pii_key() -> bytes:
    """
    【階層2】システム共通鍵（DEK）を取得する。
    """
    key = os.environ.get('PII_ENCRYPTION_KEY')
    if not key:
        # 開発用デフォルトキー
        key = b'bA-sTq-mG8_dK9-7_wN-xZ_yB_vC-1D-2E_fG_hI_j='
    return key if isinstance(key, bytes) else key.encode('utf-8')


# ====================================================================
# 2. 認証・権限サービス (Auth & RBAC)
# ====================================================================

def authenticate_supporter(email, password):
    """職員のログイン認証"""
    # Supporter -> SupporterPII を結合して検索
    supporter = Supporter.query.join(Supporter.pii).filter(SupporterPII.email == email).first()
    
    if supporter and supporter.pii and supporter.pii.check_password(password):
        return supporter
    return None

def check_permission(supporter_id, permission_name):
    """
    職員が特定の権限(Permission)を持っているか確認する。
    """
    supporter = db.session.get(Supporter, supporter_id)
    if not supporter:
        return False
    
    # 職員が持つ全てのロールから、権限セットを収集
    for role in supporter.roles:
        for perm in role.permissions:
            if perm.name == permission_name:
                return True
    
    return False