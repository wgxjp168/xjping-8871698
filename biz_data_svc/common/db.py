"""
数据库连接管理器（单例 + 上下文管理器）
"""
import sqlite3
from typing import Optional

from ..config import Settings


class Database:
    """线程安全的 SQLite 连接单例"""

    _instance: Optional['Database'] = None

    def __new__(cls, settings: Optional[Settings] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = settings or Settings()
            cls._instance._conn: Optional[sqlite3.Connection] = None
        return cls._instance

    # ------------------------------------------------------------------ #

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._settings.db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute('PRAGMA foreign_keys = ON')
            self._conn.execute('PRAGMA journal_mode = WAL')
        return self._conn

    def execute(self, sql: str, params=()):
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_seq):
        return self.conn.executemany(sql, params_seq)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            Database._instance = None

    # ------------------------------------------------------------------ #
    #  上下文管理器（事务块）                                                  #
    # ------------------------------------------------------------------ #

    def transaction(self):
        """with db.transaction(): ... 出现异常自动回滚"""
        return _Transaction(self)


class _Transaction:
    def __init__(self, db: Database):
        self._db = db

    def __enter__(self):
        return self._db

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._db.commit()
        else:
            self._db.rollback()
        return False   # 不吞异常
