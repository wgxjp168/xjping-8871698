from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import User, UserSession


class UserRepository(BaseRepository[User]):
    """用户数据存储层（含会话管理）"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'users'

    def _from_row(self, row) -> User:
        return User.from_row(row)

    # ---- 写 ----

    def add(self, user: User) -> User:
        cur = self._db.execute(
            '''INSERT INTO users (tenant_id,username,password,email,phone,avatar_url,is_active)
               VALUES (?,?,?,?,?,?,?)''',
            (user.tenant_id, user.username, user.password, user.email,
             user.phone, user.avatar_url, user.is_active),
        )
        self._db.commit()
        user.id = cur.lastrowid
        return user

    def update(self, user: User) -> bool:
        cur = self._db.execute(
            '''UPDATE users SET username=?,email=?,phone=?,avatar_url=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (user.username, user.email, user.phone, user.avatar_url, user.id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def update_password(self, user_id: int, new_password: str) -> bool:
        cur = self._db.execute(
            'UPDATE users SET password=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (new_password, user_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def set_active(self, user_id: int, is_active: bool) -> bool:
        cur = self._db.execute(
            'UPDATE users SET is_active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (1 if is_active else 0, user_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ---- 读 ----

    def find_by_tenant(self, tenant_id: int) -> List[User]:
        return self._fetchall('SELECT * FROM users WHERE tenant_id=? ORDER BY id', (tenant_id,))

    def find_by_username(self, tenant_id: int, username: str) -> Optional[User]:
        return self._fetchone(
            'SELECT * FROM users WHERE tenant_id=? AND username=?', (tenant_id, username))

    def find_by_email(self, tenant_id: int, email: str) -> Optional[User]:
        return self._fetchone(
            'SELECT * FROM users WHERE tenant_id=? AND email=?', (tenant_id, email))

    def authenticate(self, tenant_id: int, username: str, password: str) -> Optional[User]:
        return self._fetchone(
            'SELECT * FROM users WHERE tenant_id=? AND username=? AND password=? AND is_active=1',
            (tenant_id, username, password),
        )

    # ---- 会话 ----

    def create_session(self, session: UserSession) -> UserSession:
        cur = self._db.execute(
            'INSERT INTO user_sessions (user_id,token,expires_at) VALUES (?,?,?)',
            (session.user_id, session.token, session.expires_at),
        )
        self._db.commit()
        session.id = cur.lastrowid
        return session

    def find_session(self, token: str) -> Optional[UserSession]:
        row = self._db.execute(
            'SELECT * FROM user_sessions WHERE token=? AND expires_at > CURRENT_TIMESTAMP',
            (token,),
        ).fetchone()
        return UserSession.from_row(row) if row else None

    def revoke_session(self, token: str) -> bool:
        cur = self._db.execute('DELETE FROM user_sessions WHERE token=?', (token,))
        self._db.commit()
        return cur.rowcount > 0

    def revoke_all_sessions(self, user_id: int) -> int:
        cur = self._db.execute('DELETE FROM user_sessions WHERE user_id=?', (user_id,))
        self._db.commit()
        return cur.rowcount
