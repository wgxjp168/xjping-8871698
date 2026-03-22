from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Tenant:
    name:       str
    code:       str
    status:     str = 'active'
    plan:       str = 'basic'
    id:         Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {'id': self.id, 'name': self.name, 'code': self.code,
                'status': self.status, 'plan': self.plan}

    @staticmethod
    def from_row(row) -> 'Tenant':
        r = tuple(row)
        t = Tenant(id=r[0], name=r[1], code=r[2], status=r[3], plan=r[4])
        t.created_at = r[5]; t.updated_at = r[6]
        return t


@dataclass
class User:
    tenant_id:  int
    username:   str
    password:   str
    email:      str
    phone:      str = ''
    avatar_url: str = ''
    is_active:  int = 1
    id:         Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {'id': self.id, 'tenant_id': self.tenant_id,
                'username': self.username, 'email': self.email,
                'phone': self.phone, 'is_active': self.is_active}

    @staticmethod
    def from_row(row) -> 'User':
        r = tuple(row)
        u = User(id=r[0], tenant_id=r[1], username=r[2], password=r[3],
                 email=r[4], phone=r[5] or '', avatar_url=r[6] or '',
                 is_active=r[7])
        u.created_at = r[8]; u.updated_at = r[9]
        return u


@dataclass
class UserSession:
    user_id:    int
    token:      str
    expires_at: str
    id:         Optional[int] = None
    created_at: Optional[str] = None

    @staticmethod
    def from_row(row) -> 'UserSession':
        r = tuple(row)
        s = UserSession(id=r[0], user_id=r[1], token=r[2], expires_at=r[3])
        s.created_at = r[4]
        return s
