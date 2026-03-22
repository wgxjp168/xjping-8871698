from typing import List, Optional, Tuple
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Order, OrderItem

_VALID_STATUS = {'pending', 'paid', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'}


class OrderRepository(BaseRepository[Order]):
    """订单数据存储层（含明细，事务创建）"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'orders'

    def _from_row(self, row) -> Order:
        return Order.from_row(row)

    # ---- 写 ----

    def create(self, order: Order) -> Order:
        """事务创建订单 + 明细"""
        with self._db.transaction():
            cur = self._db.execute(
                '''INSERT INTO orders
                   (tenant_id,mall_id,customer_id,order_no,total_amount,
                    discount_amount,pay_amount,status,remark)
                   VALUES (?,?,?,?,?,?,?,?,?)''',
                (order.tenant_id, order.mall_id, order.customer_id, order.order_no,
                 order.total_amount, order.discount_amount, order.pay_amount,
                 order.status, order.remark),
            )
            order.id = cur.lastrowid
            for item in order.items:
                item.order_id = order.id
                ic = self._db.execute(
                    '''INSERT INTO order_items
                       (order_id,product_id,product_name,quantity,unit_price,subtotal)
                       VALUES (?,?,?,?,?,?)''',
                    (item.order_id, item.product_id, item.product_name,
                     item.quantity, item.unit_price, item.subtotal),
                )
                item.id = ic.lastrowid
        return order

    def update_status(self, order_id: int, status: str) -> bool:
        if status not in _VALID_STATUS:
            raise ValueError(f'无效状态: {status}')
        cur = self._db.execute(
            'UPDATE orders SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (status, order_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ---- 读 ----

    def find_by_id(self, order_id: int) -> Optional[Order]:
        order = self._fetchone('SELECT * FROM orders WHERE id=?', (order_id,))
        if order:
            order.items = self._load_items(order_id)
        return order

    def find_by_order_no(self, order_no: str) -> Optional[Order]:
        order = self._fetchone('SELECT * FROM orders WHERE order_no=?', (order_no,))
        if order:
            order.items = self._load_items(order.id)
        return order

    def find_by_customer(self, customer_id: int) -> List[Order]:
        orders = self._fetchall(
            'SELECT * FROM orders WHERE customer_id=? ORDER BY created_at DESC',
            (customer_id,),
        )
        for o in orders:
            o.items = self._load_items(o.id)
        return orders

    def find_by_status(self, tenant_id: int, status: str) -> List[Order]:
        return self._fetchall(
            'SELECT * FROM orders WHERE tenant_id=? AND status=? ORDER BY created_at DESC',
            (tenant_id, status),
        )

    def find_by_tenant(self, tenant_id: int) -> List[Order]:
        return self._fetchall(
            'SELECT * FROM orders WHERE tenant_id=? ORDER BY created_at DESC', (tenant_id,))

    def paginate_by_tenant(self, tenant_id: int, page: int = 1,
                           size: int = 20) -> Tuple[List[Order], int]:
        return self.paginate(page, size, 'tenant_id=?', (tenant_id,))

    def _load_items(self, order_id: int) -> List[OrderItem]:
        rows = self._db.execute(
            'SELECT * FROM order_items WHERE order_id=? ORDER BY id', (order_id,)).fetchall()
        return [OrderItem.from_row(r) for r in rows]
