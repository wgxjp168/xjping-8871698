from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CartItem:
    """购物车商品模型"""
    user_id: int
    product_id: int
    quantity: int
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'created_at': str(self.created_at) if self.created_at else None,
        }

    @staticmethod
    def from_row(row: tuple) -> 'CartItem':
        item = CartItem(
            id=row[0],
            user_id=row[1],
            product_id=row[2],
            quantity=row[3],
        )
        item.created_at = row[4]
        return item
