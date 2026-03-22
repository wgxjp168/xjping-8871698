from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Shop


class ShopRepository(BaseRepository[Shop]):
    """铺位数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'shops'

    def _from_row(self, row) -> Shop:
        return Shop.from_row(row)

    def add(self, shop: Shop) -> Shop:
        cur = self._db.execute(
            '''INSERT INTO shops (mall_id,floor_id,name,shop_no,area,status)
               VALUES (?,?,?,?,?,?)''',
            (shop.mall_id, shop.floor_id, shop.name, shop.shop_no, shop.area, shop.status),
        )
        self._db.commit()
        shop.id = cur.lastrowid
        return shop

    def update_status(self, shop_id: int, status: str) -> bool:
        cur = self._db.execute(
            'UPDATE shops SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (status, shop_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def find_by_mall(self, mall_id: int) -> List[Shop]:
        return self._fetchall('SELECT * FROM shops WHERE mall_id=? ORDER BY shop_no', (mall_id,))

    def find_vacant(self, mall_id: int) -> List[Shop]:
        return self._fetchall(
            "SELECT * FROM shops WHERE mall_id=? AND status='vacant' ORDER BY shop_no",
            (mall_id,),
        )

    def find_by_floor(self, floor_id: int) -> List[Shop]:
        return self._fetchall('SELECT * FROM shops WHERE floor_id=? ORDER BY shop_no', (floor_id,))

    def find_by_shop_no(self, mall_id: int, shop_no: str) -> Optional[Shop]:
        return self._fetchone(
            'SELECT * FROM shops WHERE mall_id=? AND shop_no=?', (mall_id, shop_no))
