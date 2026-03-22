"""
用户 Repository
继承 BaseRepository[User]，提供用户表及会话表完整操作。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import User, UserSession


class UserRepository(BaseRepository[User]):
    """users 表（及 user_sessions 表）的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'users'

    def _from_row(self, row) -> User:
        return User.from_row(row)

    # ------------------------------------------------------------------ #
    #  注册与基本写操作                                                       #
    # ------------------------------------------------------------------ #

    def register(self, user: User) -> User:
        """
        插入新用户。
        若用户名/邮箱/手机在同一租户内已存在，抛出 ValueError。
        """
        # 唯一性校验
        if self.find_by_username(user.tenant_id, user.username):
            raise ValueError(
                f"用户名 '{user.username}' 在租户 {user.tenant_id} 内已存在"
            )
        if user.email and self.find_by_email(user.tenant_id, user.email):
            raise ValueError(
                f"邮箱 '{user.email}' 在租户 {user.tenant_id} 内已存在"
            )
        if user.phone and self.find_by_phone(user.tenant_id, user.phone):
            raise ValueError(
                f"手机号 '{user.phone}' 在租户 {user.tenant_id} 内已存在"
            )

        sql = '''
            INSERT INTO users
                (tenant_id, username, password_hash, email, phone,
                 real_name, avatar_url, gender, birthday, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            user.tenant_id,
            user.username,
            user.password_hash,
            user.email,
            user.phone,
            user.real_name,
            user.avatar_url,
            user.gender,
            user.birthday,
            user.status,
        )
        cur = self._db.execute(sql, params)
        self._db.commit()
        user.id = cur.lastrowid
        return user

    def update_profile(self, user: User) -> bool:
        """更新用户资料：real_name, phone, email, avatar_url, gender, birthday"""
        sql = '''
            UPDATE users
            SET real_name  = ?,
                phone      = ?,
                email      = ?,
                avatar_url = ?,
                gender     = ?,
                birthday   = ?
            WHERE id = ?
        '''
        params = (
            user.real_name,
            user.phone,
            user.email,
            user.avatar_url,
            user.gender,
            user.birthday,
            user.id,
        )
        cur = self._db.execute(sql, params)
        self._db.commit()
        return cur.rowcount > 0

    def update_password(self, user_id: int, new_hash: str) -> bool:
        """更新密码哈希"""
        cur = self._db.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (new_hash, user_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def set_status(self, user_id: int, status: int) -> bool:
        """设置用户状态（0=禁用 1=启用）"""
        cur = self._db.execute(
            'UPDATE users SET status = ? WHERE id = ?',
            (status, user_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def update_last_login(self, user_id: int) -> bool:
        """将 last_login_at 更新为当前时间（数据库 CURRENT_TIMESTAMP）"""
        cur = self._db.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, user_id: int) -> bool:  # noqa: A002
        """删除用户记录"""
        cur = self._db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, user_id: int) -> Optional[User]:
        """按主键查询用户"""
        return self._fetchone(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        )

    def find_by_username(self, tenant_id: int, username: str) -> Optional[User]:
        """按租户+用户名查询"""
        return self._fetchone(
            'SELECT * FROM users WHERE tenant_id = ? AND username = ?',
            (tenant_id, username),
        )

    def find_by_email(self, tenant_id: int, email: str) -> Optional[User]:
        """按租户+邮箱查询"""
        return self._fetchone(
            'SELECT * FROM users WHERE tenant_id = ? AND email = ?',
            (tenant_id, email),
        )

    def find_by_phone(self, tenant_id: int, phone: str) -> Optional[User]:
        """按租户+手机号查询"""
        return self._fetchone(
            'SELECT * FROM users WHERE tenant_id = ? AND phone = ?',
            (tenant_id, phone),
        )

    def find_by_tenant(
        self, tenant_id: int, status: Optional[int] = None
    ) -> List[User]:
        """
        查询某租户下的所有用户。
        可选 status 过滤（0=禁用 1=启用）。
        """
        if status is None:
            return self._fetchall(
                'SELECT * FROM users WHERE tenant_id = ? ORDER BY id',
                (tenant_id,),
            )
        return self._fetchall(
            'SELECT * FROM users WHERE tenant_id = ? AND status = ? ORDER BY id',
            (tenant_id, status),
        )

    def authenticate(
        self, tenant_id: int, username: str, password_hash: str
    ) -> Optional[User]:
        """
        验证登录凭据。
        匹配 tenant_id + username + password_hash + status=1 时返回 User，否则 None。
        """
        return self._fetchone(
            '''SELECT * FROM users
               WHERE tenant_id = ? AND username = ?
                 AND password_hash = ? AND status = ?''',
            (tenant_id, username, password_hash, 'active'),
        )

    # ------------------------------------------------------------------ #
    #  会话操作（user_sessions 表）                                          #
    # ------------------------------------------------------------------ #

    def create_session(self, session: UserSession) -> UserSession:
        """创建新会话记录，返回带 id 的 UserSession"""
        sql = '''
            INSERT INTO user_sessions
                (user_id, token, refresh_token, device_type,
                 ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            session.user_id,
            session.token,
            session.refresh_token,
            session.device_type,
            session.ip_address,
            session.user_agent,
            session.expires_at,
        )
        cur = self._db.execute(sql, params)
        self._db.commit()
        session.id = cur.lastrowid
        return session

    def find_session(self, token: str) -> Optional[UserSession]:
        """按 token 查询会话"""
        row = self._db.execute(
            'SELECT * FROM user_sessions WHERE token = ?', (token,)
        ).fetchone()
        return UserSession.from_row(row) if row else None

    def revoke_session(self, token: str) -> bool:
        """撤销（删除）指定 token 的会话"""
        cur = self._db.execute(
            'DELETE FROM user_sessions WHERE token = ?', (token,)
        )
        self._db.commit()
        return cur.rowcount > 0

    def revoke_all_sessions(self, user_id: int) -> int:
        """撤销某用户的所有会话，返回被删除的记录数"""
        cur = self._db.execute(
            'DELETE FROM user_sessions WHERE user_id = ?', (user_id,)
        )
        self._db.commit()
        return cur.rowcount
