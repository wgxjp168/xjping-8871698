from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Role, Permission


class RoleRepository(BaseRepository[Role]):
    """角色与权限数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'roles'

    def _from_row(self, row) -> Role:
        return Role.from_row(row)

    # ---- 权限 ----

    def ensure_permission(self, code: str, description: str = '') -> Permission:
        """确保权限存在，不存在则创建"""
        row = self._db.execute(
            'SELECT * FROM permissions WHERE code=?', (code,)).fetchone()
        if row:
            return Permission.from_row(row)
        cur = self._db.execute(
            'INSERT INTO permissions (code,description) VALUES (?,?)', (code, description))
        self._db.commit()
        return Permission(id=cur.lastrowid, code=code, description=description)

    def list_permissions(self) -> List[Permission]:
        rows = self._db.execute('SELECT * FROM permissions ORDER BY code').fetchall()
        return [Permission.from_row(r) for r in rows]

    # ---- 角色 ----

    def add(self, role: Role) -> Role:
        cur = self._db.execute(
            'INSERT INTO roles (tenant_id,name,description) VALUES (?,?,?)',
            (role.tenant_id, role.name, role.description),
        )
        self._db.commit()
        role.id = cur.lastrowid
        return role

    def update(self, role: Role) -> bool:
        cur = self._db.execute(
            'UPDATE roles SET name=?,description=? WHERE id=?',
            (role.name, role.description, role.id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def find_by_tenant(self, tenant_id: int) -> List[Role]:
        roles = self._fetchall('SELECT * FROM roles WHERE tenant_id=? ORDER BY id', (tenant_id,))
        for role in roles:
            role.permissions = self._load_permissions(role.id)
        return roles

    def find_by_name(self, tenant_id: int, name: str) -> Optional[Role]:
        role = self._fetchone(
            'SELECT * FROM roles WHERE tenant_id=? AND name=?', (tenant_id, name))
        if role:
            role.permissions = self._load_permissions(role.id)
        return role

    # ---- 角色-权限关联 ----

    def assign_permission(self, role_id: int, permission_id: int) -> bool:
        try:
            self._db.execute(
                'INSERT OR IGNORE INTO role_permissions (role_id,permission_id) VALUES (?,?)',
                (role_id, permission_id),
            )
            self._db.commit()
            return True
        except Exception:
            self._db.rollback()
            return False

    def revoke_permission(self, role_id: int, permission_id: int) -> bool:
        cur = self._db.execute(
            'DELETE FROM role_permissions WHERE role_id=? AND permission_id=?',
            (role_id, permission_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def _load_permissions(self, role_id: int) -> List[Permission]:
        rows = self._db.execute(
            '''SELECT p.* FROM permissions p
               JOIN role_permissions rp ON rp.permission_id=p.id
               WHERE rp.role_id=? ORDER BY p.code''',
            (role_id,),
        ).fetchall()
        return [Permission.from_row(r) for r in rows]
