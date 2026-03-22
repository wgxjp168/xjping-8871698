from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Mall, Floor


class MallRepository(BaseRepository[Mall]):
    """商场数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'malls'

    def _from_row(self, row) -> Mall:
        return Mall.from_row(row)

    # ---- 写 ----

    def add(self, mall: Mall) -> Mall:
        cur = self._db.execute(
            '''INSERT INTO malls (tenant_id,name,address,city,province,phone,status)
               VALUES (?,?,?,?,?,?,?)''',
            (mall.tenant_id, mall.name, mall.address, mall.city,
             mall.province, mall.phone, mall.status),
        )
        self._db.commit()
        mall.id = cur.lastrowid
        return mall

    def update(self, mall: Mall) -> bool:
        cur = self._db.execute(
            '''UPDATE malls SET name=?,address=?,city=?,province=?,phone=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (mall.name, mall.address, mall.city, mall.province, mall.phone, mall.id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def update_status(self, mall_id: int, status: str) -> bool:
        cur = self._db.execute(
            'UPDATE malls SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (status, mall_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ---- 读 ----

    def find_by_tenant(self, tenant_id: int) -> List[Mall]:
        return self._fetchall('SELECT * FROM malls WHERE tenant_id=? ORDER BY id', (tenant_id,))

    def find_by_city(self, city: str) -> List[Mall]:
        return self._fetchall(
            "SELECT * FROM malls WHERE city=? AND status='open' ORDER BY id", (city,))

    # ---- 楼层 ----

    def add_floor(self, floor: Floor) -> Floor:
        cur = self._db.execute(
            'INSERT INTO floors (mall_id,floor_no,description) VALUES (?,?,?)',
            (floor.mall_id, floor.floor_no, floor.description),
        )
        self._db.commit()
        floor.id = cur.lastrowid
        return floor

    def list_floors(self, mall_id: int) -> List[Floor]:
        rows = self._db.execute(
            'SELECT * FROM floors WHERE mall_id=? ORDER BY floor_no', (mall_id,)
        ).fetchall()
        return [Floor.from_row(r) for r in rows]
