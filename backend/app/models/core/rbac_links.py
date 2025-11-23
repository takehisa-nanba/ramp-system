# backend/app/models/core/rbac_links.py

from backend.app.extensions import db
from sqlalchemy import Column, Integer, ForeignKey, Table

# ====================================================================
# 1. SupporterRoleLink (職員と役割の連携)
# ====================================================================
# 責務: 職員(Supporter)と役割(RoleMaster)の多対多（N:M）関係を定義する。
supporter_role_link = Table(
    'supporter_role_link',
    db.metadata,
    Column('supporter_id', Integer, ForeignKey('supporters.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('role_master.id'), primary_key=True)
)

# ====================================================================
# 2. RolePermissionLink (役割と権限の連携)
# ====================================================================
# 責務: 役割(RoleMaster)と権限(PermissionMaster)の多対多（N:M）関係を定義する。
role_permission_link = Table(
    'role_permission_link',
    db.metadata,
    Column('role_id', Integer, ForeignKey('role_master.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permission_master.id'), primary_key=True)
)