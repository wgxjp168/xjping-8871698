from dataclasses import dataclass
from typing import Optional


@dataclass
class Warehouse:
    tenant_id: int
    name:      str
    address:   str = ''
    mall_id:   Optional[int] = None
    id:        Optional[int] = None

    @staticmethod
    def from_row(row) -> 'Warehouse':
        r = tuple(row)
        return Warehouse(id=r[0], tenant_id=r[1], mall_id=r[2],
                         name=r[3], address=r[4] or '')


@dataclass
class Inventory:
    warehouse_id:  int
    product_id:    int
    quantity:      int = 0
    safety_stock:  int = 0
    id:            Optional[int] = None
    updated_at:    Optional[str] = None

    @property
    def below_safety(self) -> bool:
        return self.quantity < self.safety_stock

    @staticmethod
    def from_row(row) -> 'Inventory':
        r = tuple(row)
        inv = Inventory(id=r[0], warehouse_id=r[1], product_id=r[2],
                        quantity=r[3], safety_stock=r[4])
        inv.updated_at = r[5]
        return inv


@dataclass
class StockMovement:
    warehouse_id:   int
    product_id:     int
    movement_type:  str          # in / out / adjust / transfer
    quantity:       int          # 正数增加，负数减少
    ref_type:       str = ''
    ref_id:         int = 0
    remark:         str = ''
    id:             Optional[int] = None
    created_at:     Optional[str] = None

    @staticmethod
    def from_row(row) -> 'StockMovement':
        r = tuple(row)
        mv = StockMovement(id=r[0], warehouse_id=r[1], product_id=r[2],
                           movement_type=r[3], quantity=r[4],
                           ref_type=r[5] or '', ref_id=r[6] or 0, remark=r[7] or '')
        mv.created_at = r[8]
        return mv
