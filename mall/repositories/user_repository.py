import sqlite3
from typing import Optional, List
from ..models.user import User


class UserRepository:
    """用户数据存储层 - 负责用户的增删改查操作"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, user: User) -> User:
        """新增用户，返回含 id 的 User 对象"""
        sql = """
            INSERT INTO users (username, password, email, phone, address)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (
            user.username, user.password, user.email,
            user.phone, user.address,
        ))
        self._conn.commit()
        user.id = cursor.lastrowid
        return user

    def update(self, user: User) -> bool:
        """更新用户信息（不含密码），返回是否更新成功"""
        sql = """
            UPDATE users
            SET username = ?, email = ?, phone = ?, address = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (
            user.username, user.email, user.phone, user.address, user.id,
        ))
        self._conn.commit()
        return cursor.rowcount > 0

    def update_password(self, user_id: int, new_password: str) -> bool:
        """更新用户密码"""
        sql = """
            UPDATE users
            SET password = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (new_password, user_id))
        self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, user_id: int) -> bool:
        """删除用户"""
        cursor = self._conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------ #
    #  读操作                                                               #
    # ------------------------------------------------------------------ #

    def find_by_id(self, user_id: int) -> Optional[User]:
        """按 id 查找用户"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return User.from_row(tuple(row)) if row else None

    def find_by_username(self, username: str) -> Optional[User]:
        """按用户名查找用户"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        return User.from_row(tuple(row)) if row else None

    def find_by_email(self, email: str) -> Optional[User]:
        """按邮箱查找用户"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        return User.from_row(tuple(row)) if row else None

    def find_all(self) -> List[User]:
        """查询所有用户"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY id')
        return [User.from_row(tuple(row)) for row in cursor.fetchall()]

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """验证用户名和密码，成功返回用户对象，失败返回 None"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, password),
        )
        row = cursor.fetchone()
        return User.from_row(tuple(row)) if row else None
