"""
通用 Repository 基类
所有业务 Repository 继承此类，统一 CRUD 模板
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar

from .db import Database

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """提供通用增删改查接口；子类只需实现抽象方法"""

    def __init__(self, db: Database):
        self._db = db

    # ------------------------------------------------------------------ #
    #  子类必须实现                                                          #
    # ------------------------------------------------------------------ #

    @property
    @abstractmethod
    def table(self) -> str:
        """目标表名"""

    @abstractmethod
    def _from_row(self, row) -> T:
        """将数据库行转换为领域对象"""

    # ------------------------------------------------------------------ #
    #  通用查询工具                                                          #
    # ------------------------------------------------------------------ #

    def _fetchone(self, sql: str, params=()) -> Optional[T]:
        row = self._db.execute(sql, params).fetchone()
        return self._from_row(row) if row else None

    def _fetchall(self, sql: str, params=()) -> List[T]:
        rows = self._db.execute(sql, params).fetchall()
        return [self._from_row(r) for r in rows]

    def _scalar(self, sql: str, params=()) -> Any:
        row = self._db.execute(sql, params).fetchone()
        return row[0] if row else None

    # ------------------------------------------------------------------ #
    #  通用 CRUD                                                           #
    # ------------------------------------------------------------------ #

    def find_by_id(self, pk: int) -> Optional[T]:
        return self._fetchone(f'SELECT * FROM {self.table} WHERE id = ?', (pk,))

    def find_all(self, order_by: str = 'id') -> List[T]:
        return self._fetchall(f'SELECT * FROM {self.table} ORDER BY {order_by}')

    def count(self) -> int:
        return self._scalar(f'SELECT COUNT(*) FROM {self.table}') or 0

    def delete(self, pk: int) -> bool:
        cur = self._db.execute(f'DELETE FROM {self.table} WHERE id = ?', (pk,))
        self._db.commit()
        return cur.rowcount > 0

    def exists(self, pk: int) -> bool:
        n = self._scalar(f'SELECT COUNT(*) FROM {self.table} WHERE id = ?', (pk,))
        return (n or 0) > 0

    # ------------------------------------------------------------------ #
    #  分页辅助                                                             #
    # ------------------------------------------------------------------ #

    def paginate(self, page: int = 1, size: int = 20,
                 where: str = '', params: tuple = ()) -> Tuple[List[T], int]:
        """
        返回 (items, total)
        page 从 1 开始
        """
        where_clause = f'WHERE {where}' if where else ''
        total = self._scalar(
            f'SELECT COUNT(*) FROM {self.table} {where_clause}', params
        ) or 0
        offset = (page - 1) * size
        items = self._fetchall(
            f'SELECT * FROM {self.table} {where_clause} ORDER BY id LIMIT ? OFFSET ?',
            params + (size, offset),
        )
        return items, total
