"""
角色与权限 Repository
继承 BaseRepository[Role]，提供角色、权限、用户-角色关联的完整操作。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Permission, Role


class RoleRepository(BaseRepository[Role]):
    """roles / permissions / user_roles / role_permissions 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'roles'

    def _from_row(self, row) -> Role:
        return Role.from_row(row)

    # ------------------------------------------------------------------ #
    #  私有辅助                                                             #
    # ------------------------------------------------------------------ #

    def _load_permissions(self, role_id: int) -> List[Permission]:
        """加载指定角色绑定的全部权限"""
        sql = '''
            SELECT p.id, p.code, p.name, p.module, p.resource, p.action, p.description
            FROM permissions p
            INNER JOIN role_permissions rp ON rp.permission_id = p.id
            WHERE rp.role_id = ?
            ORDER BY p.id
        '''
        rows = self._db.execute(sql, (role_id,)).fetchall()
        return [Permission.from_row(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  角色写操作                                                           #
    # ------------------------------------------------------------------ #

    def add(self, role: Role) -> Role:
        """插入新角色，返回带 id 的 Role 对象"""
        sql = '''
            INSERT INTO roles
                (tenant_id, name, code, description, is_system, status)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        params = (
            role.tenant_id,
            role.name,
            role.code,
            role.description,
            role.is_system,
            role.status,
        )
        cur = self._db.execute(sql, params)
        self._db.commit()
        role.id = cur.lastrowid
        return role

    def update(self, role: Role) -> bool:
        """更新角色基本信息（name, description, status）"""
        sql = '''
            UPDATE roles
            SET name        = ?,
                description = ?,
                status      = ?
            WHERE id = ?
        '''
        params = (
            role.name,
            role.description,
            role.status,
            role.id,
        )
        cur = self._db.execute(sql, params)
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, role_id: int) -> bool:
        """删除角色（级联关联数据需由外键约束或调用方处理）"""
        cur = self._db.execute('DELETE FROM roles WHERE id = ?', (role_id,))
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  角色查询操作                                                          #
    # ------------------------------------------------------------------ #

    def find_by_id(self, role_id: int) -> Optional[Role]:  # noqa: A002
        """按主键查询角色，附带 permissions 列表"""
        row = self._db.execute(
            'SELECT * FROM roles WHERE id = ?', (role_id,)
        ).fetchone()
        if row is None:
            return None
        role = Role.from_row(row)
        role.permissions = self._load_permissions(role.id)
        return role

    def find_by_tenant(self, tenant_id: int) -> List[Role]:
        """查询某租户下的所有角色，每个 Role 附带 permissions 列表"""
        rows = self._db.execute(
            'SELECT * FROM roles WHERE tenant_id = ? ORDER BY id',
            (tenant_id,),
        ).fetchall()
        roles = []
        for row in rows:
            role = Role.from_row(row)
            role.permissions = self._load_permissions(role.id)
            roles.append(role)
        return roles

    def find_by_code(self, tenant_id: int, code: str) -> Optional[Role]:
        """按租户+角色编码查询，不附带 permissions（轻量查询）"""
        row = self._db.execute(
            'SELECT * FROM roles WHERE tenant_id = ? AND code = ?',
            (tenant_id, code),
        ).fetchone()
        return Role.from_row(row) if row else None

    # ------------------------------------------------------------------ #
    #  权限管理                                                             #
    # ------------------------------------------------------------------ #

    def ensure_permission(
        self,
        code: str,
        name: str,
        module: str,
        resource: str,
        action: str,
        description: str = '',
    ) -> Permission:
        """
        幂等地确保权限记录存在。
        若已存在则直接返回，若不存在则插入后返回。
        """
        row = self._db.execute(
            'SELECT * FROM permissions WHERE code = ?', (code,)
        ).fetchone()
        if row:
            return Permission.from_row(row)

        sql = '''
            INSERT INTO permissions (code, name, module, resource, action, description)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        cur = self._db.execute(sql, (code, name, module, resource, action, description))
        self._db.commit()
        perm_id = cur.lastrowid
        return Permission(
            id=perm_id,
            code=code,
            name=name,
            module=module,
            resource=resource,
            action=action,
            description=description,
        )

    def list_permissions(self) -> List[Permission]:
        """查询所有权限，按 id 排序"""
        rows = self._db.execute(
            'SELECT * FROM permissions ORDER BY id'
        ).fetchall()
        return [Permission.from_row(r) for r in rows]

    def assign_permission(self, role_id: int, permission_id: int) -> bool:
        """为角色绑定权限（INSERT OR IGNORE，已绑定不报错）"""
        cur = self._db.execute(
            'INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
            (role_id, permission_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def revoke_permission(self, role_id: int, permission_id: int) -> bool:
        """解除角色与权限的绑定"""
        cur = self._db.execute(
            'DELETE FROM role_permissions WHERE role_id = ? AND permission_id = ?',
            (role_id, permission_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  用户-角色关联操作                                                      #
    # ------------------------------------------------------------------ #

    def assign_role_to_user(
        self,
        user_id: int,
        role_id: int,
        granted_by: Optional[int] = None,
    ) -> bool:
        """为用户分配角色（INSERT OR IGNORE，已分配不报错）"""
        cur = self._db.execute(
            '''INSERT OR IGNORE INTO user_roles (user_id, role_id, granted_by)
               VALUES (?, ?, ?)''',
            (user_id, role_id, granted_by),
        )
        self._db.commit()
        return cur.rowcount > 0

    def revoke_role_from_user(self, user_id: int, role_id: int) -> bool:
        """撤销用户的某个角色"""
        cur = self._db.execute(
            'DELETE FROM user_roles WHERE user_id = ? AND role_id = ?',
            (user_id, role_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def get_user_roles(self, user_id: int) -> List[Role]:
        """查询用户拥有的所有角色（不含 permissions）"""
        sql = '''
            SELECT r.id, r.tenant_id, r.name, r.code, r.description,
                   r.is_system, r.status, r.created_at
            FROM roles r
            INNER JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = ?
            ORDER BY r.id
        '''
        rows = self._db.execute(sql, (user_id,)).fetchall()
        return [Role.from_row(r) for r in rows]

    def get_user_permissions(self, user_id: int) -> List[Permission]:
        """通过用户持有的角色，获取用户的所有权限（去重）"""
        sql = '''
            SELECT DISTINCT p.id, p.code, p.name, p.module,
                            p.resource, p.action, p.description
            FROM permissions p
            INNER JOIN role_permissions rp ON rp.permission_id = p.id
            INNER JOIN user_roles ur ON ur.role_id = rp.role_id
            WHERE ur.user_id = ?
            ORDER BY p.id
        '''
        rows = self._db.execute(sql, (user_id,)).fetchall()
        return [Permission.from_row(r) for r in rows]

    def has_permission(self, user_id: int, permission_code: str) -> bool:
        """判断用户是否拥有指定权限码对应的权限"""
        sql = '''
            SELECT COUNT(*)
            FROM permissions p
            INNER JOIN role_permissions rp ON rp.permission_id = p.id
            INNER JOIN user_roles ur ON ur.role_id = rp.role_id
            WHERE ur.user_id = ? AND p.code = ?
        '''
        row = self._db.execute(sql, (user_id, permission_code)).fetchone()
        return (row[0] if row else 0) > 0
