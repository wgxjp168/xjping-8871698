from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class OrderItem:
    """订单商品明细模型"""
    order_id: int
    product_id: int
    quantity: int
    unit_price: float
    id: Optional[int] = None

    @property
    def subtotal(self) -> float:
        return self.unit_price * self.quantity

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'subtotal': self.subtotal,
        }

    @staticmethod
    def from_row(row: tuple) -> 'OrderItem':
        return OrderItem(
            id=row[0],
            order_id=row[1],
            product_id=row[2],
            quantity=row[3],
            unit_price=row[4],
        )


@dataclass
class Order:
    """订单模型

    status 取值:
        pending   - 待付款
        paid      - 已付款
        shipped   - 已发货
        delivered - 已收货
        cancelled - 已取消
    """
    user_id: int
    total_amount: float
    address: str
    status: str = 'pending'
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[OrderItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'total_amount': self.total_amount,
            'address': self.address,
            'status': self.status,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None,
            'items': [item.to_dict() for item in self.items],
        }

    @staticmethod
    def from_row(row: tuple) -> 'Order':
        order = Order(
            id=row[0],
            user_id=row[1],
            total_amount=row[2],
            address=row[3],
            status=row[4],
        )
        order.created_at = row[5]
        order.updated_at = row[6]
        return order
