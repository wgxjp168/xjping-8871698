"""
用户与租户模块 — 领域模型
所有模型均为 dataclass，提供 to_dict() 和 from_row() 方法。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
#  Tenant                                                                      #
# --------------------------------------------------------------------------- #

@dataclass
class Tenant:
    """租户"""
    name: str
    code: str
    id: Optional[int] = None
    status: str = 'active'          # active / suspended / cancelled
    plan: str = 'basic'             # basic / pro / enterprise
    contact_name: str = ''
    contact_phone: str = ''
    contact_email: str = ''
    address: str = ''
    logo_url: str = ''
    expired_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'status': self.status,
            'plan': self.plan,
            'contact_name': self.contact_name,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'address': self.address,
            'logo_url': self.logo_url,
            'expired_at': self.expired_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def from_row(row) -> 'Tenant':
        """
        列顺序：id, name, code, status, plan,
                contact_name, contact_phone, contact_email,
                address, logo_url, expired_at, created_at, updated_at
        """
        r = tuple(row)
        return Tenant(
            id=r[0],
            name=r[1],
            code=r[2],
            status=r[3],
            plan=r[4],
            contact_name=r[5],
            contact_phone=r[6],
            contact_email=r[7],
            address=r[8],
            logo_url=r[9],
            expired_at=r[10],
            created_at=r[11],
            updated_at=r[12],
        )


# --------------------------------------------------------------------------- #
#  User                                                                        #
# --------------------------------------------------------------------------- #

@dataclass
class User:
    """用户"""
    tenant_id: int
    username: str
    password_hash: str
    id: Optional[int] = None
    email: str = ''
    phone: str = ''
    real_name: str = ''
    avatar_url: str = ''
    gender: str = 'unknown'         # male / female / unknown
    birthday: Optional[str] = None
    status: str = 'active'          # active / disabled / pending
    last_login_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'username': self.username,
            'password_hash': self.password_hash,
            'email': self.email,
            'phone': self.phone,
            'real_name': self.real_name,
            'avatar_url': self.avatar_url,
            'gender': self.gender,
            'birthday': self.birthday,
            'status': self.status,
            'last_login_at': self.last_login_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def from_row(row) -> 'User':
        """
        列顺序：id, tenant_id, username, password_hash, email,
                phone, real_name, avatar_url, gender, birthday,
                status, last_login_at, created_at, updated_at
        """
        r = tuple(row)
        return User(
            id=r[0],
            tenant_id=r[1],
            username=r[2],
            password_hash=r[3],
            email=r[4],
            phone=r[5],
            real_name=r[6],
            avatar_url=r[7],
            gender=r[8],
            birthday=r[9],
            status=r[10],
            last_login_at=r[11],
            created_at=r[12],
            updated_at=r[13],
        )


# --------------------------------------------------------------------------- #
#  Role                                                                        #
# --------------------------------------------------------------------------- #

@dataclass
class Role:
    """角色"""
    tenant_id: int
    name: str
    code: str
    id: Optional[int] = None
    description: str = ''
    is_system: int = 0              # 0=自定义 1=系统内置
    status: str = 'active'          # active / disabled
    created_at: Optional[str] = None
    permissions: List['Permission'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'is_system': self.is_system,
            'status': self.status,
            'created_at': self.created_at,
            'permissions': [p.to_dict() for p in self.permissions],
        }

    @staticmethod
    def from_row(row) -> 'Role':
        """
        列顺序：id, tenant_id, name, code, description,
                is_system, status, created_at
        """
        r = tuple(row)
        return Role(
            id=r[0],
            tenant_id=r[1],
            name=r[2],
            code=r[3],
            description=r[4],
            is_system=r[5],
            status=r[6],
            created_at=r[7],
        )


# --------------------------------------------------------------------------- #
#  Permission                                                                  #
# --------------------------------------------------------------------------- #

@dataclass
class Permission:
    """权限"""
    code: str
    name: str
    id: Optional[int] = None
    module: str = ''
    resource: str = ''
    action: str = ''
    description: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'module': self.module,
            'resource': self.resource,
            'action': self.action,
            'description': self.description,
        }

    @staticmethod
    def from_row(row) -> 'Permission':
        """
        列顺序：id, code, name, module, resource, action, description
        """
        r = tuple(row)
        return Permission(
            id=r[0],
            code=r[1],
            name=r[2],
            module=r[3],
            resource=r[4],
            action=r[5],
            description=r[6],
        )


# --------------------------------------------------------------------------- #
#  UserRole                                                                    #
# --------------------------------------------------------------------------- #

@dataclass
class UserRole:
    """用户-角色关联"""
    user_id: int
    role_id: int
    granted_by: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'role_id': self.role_id,
            'granted_by': self.granted_by,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'UserRole':
        """列顺序：user_id, role_id, granted_by, created_at"""
        r = tuple(row)
        return UserRole(
            user_id=r[0],
            role_id=r[1],
            granted_by=r[2],
            created_at=r[3],
        )


# --------------------------------------------------------------------------- #
#  RolePermission                                                              #
# --------------------------------------------------------------------------- #

@dataclass
class RolePermission:
    """角色-权限关联"""
    role_id: int
    permission_id: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'role_id': self.role_id,
            'permission_id': self.permission_id,
        }

    @staticmethod
    def from_row(row) -> 'RolePermission':
        """列顺序：role_id, permission_id"""
        r = tuple(row)
        return RolePermission(
            role_id=r[0],
            permission_id=r[1],
        )


# --------------------------------------------------------------------------- #
#  UserSession                                                                 #
# --------------------------------------------------------------------------- #

@dataclass
class UserSession:
    """用户会话"""
    user_id: int
    token: str
    expires_at: str
    id: Optional[int] = None
    refresh_token: Optional[str] = None
    device_type: str = 'web'        # web / ios / android / api
    ip_address: str = ''
    user_agent: str = ''
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'token': self.token,
            'refresh_token': self.refresh_token,
            'device_type': self.device_type,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'expires_at': self.expires_at,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'UserSession':
        """
        列顺序：id, user_id, token, refresh_token, device_type,
                ip_address, user_agent, expires_at, created_at
        """
        r = tuple(row)
        return UserSession(
            id=r[0],
            user_id=r[1],
            token=r[2],
            refresh_token=r[3],
            device_type=r[4],
            ip_address=r[5],
            user_agent=r[6],
            expires_at=r[7],
            created_at=r[8],
        )
