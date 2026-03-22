from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Inventory, StockMovement


class InventoryRepository(BaseRepository[Inventory]):
    """库存数据存储层（含出入库流水）"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'inventory'

    def _from_row(self, row) -> Inventory:
        return Inventory.from_row(row)

    # ---- 库存初始化 ----

    def init_stock(self, inventory: Inventory) -> Inventory:
        """初始化某商品在某仓库的库存记录（已存在则忽略）"""
        self._db.execute(
            '''INSERT OR IGNORE INTO inventory
               (warehouse_id,product_id,quantity,safety_stock)
               VALUES (?,?,?,?)''',
            (inventory.warehouse_id, inventory.product_id,
             inventory.quantity, inventory.safety_stock),
        )
        self._db.commit()
        inv = self.find_by_warehouse_product(inventory.warehouse_id, inventory.product_id)
        return inv or inventory

    # ---- 库存变动（事务） ----

    def move_stock(self, warehouse_id: int, product_id: int, delta: int,
                   movement_type: str, ref_type: str = '', ref_id: int = 0,
                   remark: str = '') -> StockMovement:
        """
        原子库存变更 + 记录流水。
        delta > 0 入库，delta < 0 出库。
        出库时若库存不足则抛 ValueError。
        """
        with self._db.transaction():
            # 查当前库存（带锁意图，SQLite 串行化所以直接查即可）
            row = self._db.execute(
                'SELECT quantity FROM inventory WHERE warehouse_id=? AND product_id=?',
                (warehouse_id, product_id),
            ).fetchone()
            if row is None:
                raise LookupError(f'仓库 {warehouse_id} 中商品 {product_id} 无库存记录')
            current = row[0]
            new_qty = current + delta
            if new_qty < 0:
                raise ValueError(f'库存不足：当前={current}，变动={delta}')
            self._db.execute(
                '''UPDATE inventory SET quantity=?, updated_at=CURRENT_TIMESTAMP
                   WHERE warehouse_id=? AND product_id=?''',
                (new_qty, warehouse_id, product_id),
            )
            cur = self._db.execute(
                '''INSERT INTO stock_movements
                   (warehouse_id,product_id,movement_type,quantity,ref_type,ref_id,remark)
                   VALUES (?,?,?,?,?,?,?)''',
                (warehouse_id, product_id, movement_type, delta,
                 ref_type, ref_id, remark),
            )
            mv_id = cur.lastrowid

        return StockMovement(
            id=mv_id, warehouse_id=warehouse_id, product_id=product_id,
            movement_type=movement_type, quantity=delta,
            ref_type=ref_type, ref_id=ref_id, remark=remark,
        )

    def set_safety_stock(self, warehouse_id: int, product_id: int, safety: int) -> bool:
        cur = self._db.execute(
            '''UPDATE inventory SET safety_stock=?, updated_at=CURRENT_TIMESTAMP
               WHERE warehouse_id=? AND product_id=?''',
            (safety, warehouse_id, product_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ---- 查询 ----

    def find_by_warehouse(self, warehouse_id: int) -> List[Inventory]:
        return self._fetchall(
            'SELECT * FROM inventory WHERE warehouse_id=? ORDER BY product_id',
            (warehouse_id,),
        )

    def find_by_warehouse_product(self, warehouse_id: int,
                                  product_id: int) -> Optional[Inventory]:
        return self._fetchone(
            'SELECT * FROM inventory WHERE warehouse_id=? AND product_id=?',
            (warehouse_id, product_id),
        )

    def find_below_safety(self, warehouse_id: int) -> List[Inventory]:
        """查询库存低于安全库存的商品"""
        return self._fetchall(
            'SELECT * FROM inventory WHERE warehouse_id=? AND quantity < safety_stock ORDER BY quantity',
            (warehouse_id,),
        )

    # ---- 流水查询 ----

    def list_movements(self, warehouse_id: int, product_id: Optional[int] = None,
                       limit: int = 100) -> List[StockMovement]:
        if product_id:
            rows = self._db.execute(
                '''SELECT * FROM stock_movements
                   WHERE warehouse_id=? AND product_id=?
                   ORDER BY created_at DESC LIMIT ?''',
                (warehouse_id, product_id, limit),
            ).fetchall()
        else:
            rows = self._db.execute(
                'SELECT * FROM stock_movements WHERE warehouse_id=? ORDER BY created_at DESC LIMIT ?',
                (warehouse_id, limit),
            ).fetchall()
        return [StockMovement.from_row(r) for r in rows]
