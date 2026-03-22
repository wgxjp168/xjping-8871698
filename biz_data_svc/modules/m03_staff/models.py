from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Permission:
    code:        str
    description: str = ''
    id:          Optional[int] = None

    @staticmethod
    def from_row(row) -> 'Permission':
        r = tuple(row)
        return Permission(id=r[0], code=r[1], description=r[2] or '')


@dataclass
class Role:
    tenant_id:   int
    name:        str
    description: str = ''
    id:          Optional[int] = None
    permissions: List[Permission] = field(default_factory=list)

    @staticmethod
    def from_row(row) -> 'Role':
        r = tuple(row)
        return Role(id=r[0], tenant_id=r[1], name=r[2], description=r[3] or '')


@dataclass
class Staff:
    tenant_id:   int
    name:        str
    employee_no: str
    mall_id:     Optional[int] = None
    user_id:     Optional[int] = None
    position:    str = ''
    phone:       str = ''
    status:      str = 'active'
    hired_at:    Optional[str] = None
    id:          Optional[int] = None
    created_at:  Optional[str] = None
    updated_at:  Optional[str] = None
    roles:       List[Role] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {'id': self.id, 'tenant_id': self.tenant_id, 'mall_id': self.mall_id,
                'name': self.name, 'employee_no': self.employee_no,
                'position': self.position, 'status': self.status,
                'roles': [r.name for r in self.roles]}

    @staticmethod
    def from_row(row) -> 'Staff':
        r = tuple(row)
        s = Staff(id=r[0], tenant_id=r[1], mall_id=r[2], user_id=r[3],
                  name=r[4], employee_no=r[5], position=r[6] or '',
                  phone=r[7] or '', status=r[8], hired_at=r[9])
        s.created_at = r[10]; s.updated_at = r[11]
        return s
