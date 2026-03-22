from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Warehouse


class WarehouseRepository(BaseRepository[Warehouse]):
    """仓库数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'warehouses'

    def _from_row(self, row) -> Warehouse:
        return Warehouse.from_row(row)

    def add(self, warehouse: Warehouse) -> Warehouse:
        cur = self._db.execute(
            'INSERT INTO warehouses (tenant_id,mall_id,name,address) VALUES (?,?,?,?)',
            (warehouse.tenant_id, warehouse.mall_id, warehouse.name, warehouse.address),
        )
        self._db.commit()
        warehouse.id = cur.lastrowid
        return warehouse

    def update(self, warehouse: Warehouse) -> bool:
        cur = self._db.execute(
            'UPDATE warehouses SET name=?,address=?,mall_id=? WHERE id=?',
            (warehouse.name, warehouse.address, warehouse.mall_id, warehouse.id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def find_by_tenant(self, tenant_id: int) -> List[Warehouse]:
        return self._fetchall(
            'SELECT * FROM warehouses WHERE tenant_id=? ORDER BY id', (tenant_id,))

    def find_by_mall(self, mall_id: int) -> List[Warehouse]:
        return self._fetchall(
            'SELECT * FROM warehouses WHERE mall_id=? ORDER BY id', (mall_id,))
