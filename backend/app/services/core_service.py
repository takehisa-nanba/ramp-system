# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from backend.app.models import (
    User, UserPII, Supporter, SupporterPII, RoleMaster, PermissionMaster,
    Corporation, ServiceCertificate, GrantedService, 
    ContractReportDetail, OfficeServiceConfiguration, OfficeSetting
)
import os
import logging

# ★ ロガーの取得
logger = logging.getLogger(__name__)

# ====================================================================
# 1. 鍵取得ロジック（暗号化の土台）
# ====================================================================

def get_corporation_id_for_user(user: User) -> int:
    """
    利用者(User)から、その利用者が「在籍」している法人(Corporation)のIDを
    「契約」を辿って特定する。
    """
    if not user:
        logger.error("❌ get_corporation_id_for_user called with None user.")
        raise ValueError("User object is required to find corporation ID.")
        
    try:
        logger.debug(f"🔍 Resolving Corporation ID for User {user.id}...")

        # 1. 直近の受給者証を探す
        latest_cert = ServiceCertificate.query.filter_by(user_id=user.id)\
            .order_by(ServiceCertificate.certificate_issue_date.desc()).first()
            
        if not latest_cert:
            logger.warning(f"⚠️ User {user.id} has no ServiceCertificate. Using default Corp ID: 1.")
            return 1 
            
        # 2. 受給者証に紐づく最新の支給決定を探す
        latest_grant = GrantedService.query.filter_by(certificate_id=latest_cert.id)\
            .order_by(GrantedService.granted_start_date.desc()).first()
            
        if not latest_grant:
            logger.warning(f"⚠️ User {user.id} has Certificate {latest_cert.id} but no GrantedService.")
            return 1
            
        # 3. 支給決定に紐づく契約詳細を探す
        contract = ContractReportDetail.query.filter_by(granted_service_id=latest_grant.id).first()
        
        if not contract:
            logger.warning(f"⚠️ User {user.id} has Grant {latest_grant.id} but no ContractReportDetail.")
            return 1
            
        # 4. 契約からサービス構成 -> 事業所 -> 法人 を辿る
        service_config = db.session.get(OfficeServiceConfiguration, contract.office_service_configuration_id)
        
        if not service_config:
            logger.error(f"❌ Contract {contract.id} points to invalid ServiceConfig {contract.office_service_configuration_id}.")
            return 1

        office = db.session.get(OfficeSetting, service_config.office_id)
        
        if office:
            logger.info(f"✅ User {user.id} belongs to Corporation {office.corporation_id} (via Office {office.id}).")
            return office.corporation_id
            
        return 1

    except Exception as e:
        logger.exception(f"🔥 CRITICAL: Failed to resolve Corporation ID for User {user.id}: {e}")
        return 1


def get_corporation_kek(corporation_id: int) -> bytes:
    """【階層1】法人のマスターキー（KEK）を取得する。"""
    logger.debug(f"🔑 Retrieving KEK for Corporation {corporation_id}...")
    
    temp_key = os.environ.get('FERNET_ENCRYPTION_KEY')
    if not temp_key:
        logger.warning("⚠️ FERNET_ENCRYPTION_KEY not set. Using insecure default key.")
        temp_key = b'sTqmG8dK97wNxZyBvC1D2EfGhIjK3L4M5N6O7P8Q9R0='
        
    return temp_key if isinstance(temp_key, bytes) else temp_key.encode('utf-8')


def get_system_pii_key() -> bytes:
    """【階層2】システム共通鍵（DEK）を取得する。"""
    key = os.environ.get('PII_ENCRYPTION_KEY')
    if not key:
        logger.critical("🔥 PII_ENCRYPTION_KEY is not set! Security compromised.")
        key = b'XyZ7aBCdEfGhIjKlMnOpQrStUvWxYz0123456789Abc='
    return key if isinstance(key, bytes) else key.encode('utf-8')


# ====================================================================
# 2. 認証・権限サービス (Auth & RBAC)
# ====================================================================

def authenticate_supporter(email, password):
    """職員のログイン認証"""
    logger.info(f"🔐 Auth attempt for: {email}")
    # Supporter -> SupporterPII を結合して検索
    # (SupporterPIIをインポート済みなので直接フィルタ可能)
    supporter = Supporter.query.join(Supporter.pii).filter(SupporterPII.email == email).first()
    
    if supporter and supporter.pii and supporter.pii.check_password(password):
        logger.info(f"✅ Auth success: Supporter {supporter.id}")
        return supporter
    
    logger.warning(f"⛔ Auth failed for: {email}")
    return None

def check_permission(supporter_id, permission_name):
    """職員が特定の権限(Permission)を持っているか確認する。"""
    supporter = db.session.get(Supporter, supporter_id)
    if not supporter:
        return False
    
    # 職員が持つ全てのロールから、権限セットを収集
    for role in supporter.roles:
        for perm in role.permissions:
            if perm.name == permission_name:
                return True
    
    return False