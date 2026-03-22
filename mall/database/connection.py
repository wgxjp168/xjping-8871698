import sqlite3
from typing import Optional


class DatabaseConnection:
    """数据库连接管理器（单例模式）"""

    _instance: Optional['DatabaseConnection'] = None

    def __new__(cls, db_path: str = 'mall.db'):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._db_path = db_path
            cls._instance._conn = None
        return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute('PRAGMA foreign_keys = ON')
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            DatabaseConnection._instance = None

    def __enter__(self):
        return self.get_connection()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
