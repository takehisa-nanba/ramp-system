# backend/app/services/core_service.py

from flask import current_app # ★この行をインポートに追加★
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
    
    # ★ 修正: os.environ -> current_app.config から読み込む
    temp_key = current_app.config.get('FERNET_ENCRYPTION_KEY')

    # FERNET_ENCRYPTION_KEYが設定されていない（FALLBACK_キーが使われている）場合は警告
    if not temp_key or temp_key.startswith('FALLBACK_'):
        logger.warning("⚠️ FERNET_ENCRYPTION_KEY not set. Using insecure default key.")
        temp_key = b'sTqmG8dK97wNxZyBvC1D2EfGhIjK3L4M5N6O7P8Q9R0='  # テスト用のデフォルトキー
        
    return temp_key if isinstance(temp_key, bytes) else temp_key.encode('utf-8')

def get_system_pii_key() -> bytes:
    """【階層2】システム共通鍵（DEK）を取得する。"""
    # ★ 修正: os.environ -> current_app.config から読み込む
    key = current_app.config.get('PII_ENCRYPTION_KEY')
    
    # PII_ENCRYPTION_KEYが設定されていない（FALLBACK_キーが使われている）場合はCRITICAL警告
    if not key or key.startswith('FALLBACK_'):
        logger.critical("🔥 PII_ENCRYPTION_KEY is not set! Security compromised.")
        key = b'XyZ7aBCdEfGhIjKlMnOpQrStUvWxYz0123456789Abc=' # テスト用のデフォルトキー

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

def authenticate_user(login_id, password):
    """利用者のログイン認証（メールアドレスまたは利用者コード）"""
    logger.info(f"🔐 User Auth attempt for: {login_id}")
    
    # 1. メールアドレスで検索
    user = User.query.join(User.pii).filter(UserPII.email == login_id).first()
    
    # 2. 見つからなければ利用者コードで検索
    if not user:
        user = User.query.filter_by(user_code=login_id).first()
        
    if user and user.pii and user.pii.check_password(password):
        logger.info(f"✅ User Auth success: User {user.id}")
        return user
    
    logger.warning(f"⛔ User Auth failed for: {login_id}")
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

def authenticate_supporter_by_code(staff_code, password):
    """
    職員コードとパスワードによるログイン認証（クイック認証用）。
    staff_code はモデル層で Unique/Not Null でロックされているため、高速検索が可能。
    """
    logger.info(f"🔐 Quick Auth attempt for Staff Code: {staff_code}")
    
    # Supporter モデルを staff_code で検索
    supporter = Supporter.query.filter_by(staff_code=staff_code).first()
    
    # 認証には SupporterPII モデルのハッシュ化パスワードが必要
    if supporter and supporter.pii and supporter.pii.check_password(password):
        logger.info(f"✅ Quick Auth success: Supporter {supporter.id}")
        return supporter
    
    logger.warning(f"⛔ Quick Auth failed for code: {staff_code}")
    return None

def check_pii_access(supporter_id: int) -> bool:
    """
    【PIIアクセス防御壁】
    職員が利用者PIIを閲覧・操作する権限（ロール）を持っているか確認する。
    """
    # 監査上、PIIアクセスは特別な権限（例: 'VIEW_PII'）でのみ許可
    has_pii_permission = check_permission(supporter_id, "VIEW_PII")
    
    if not has_pii_permission:
        logger.warning(f"🚫 Supporter {supporter_id} attempted PII access without VIEW_PII permission.")
        return False
    
    logger.debug(f"✅ Supporter {supporter_id} has PII access.")
    return True