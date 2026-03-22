from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Product:
    """商品模型"""
    name: str
    price: float
    stock: int
    category_id: int
    description: str = ''
    image_url: str = ''
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'stock': self.stock,
            'category_id': self.category_id,
            'description': self.description,
            'image_url': self.image_url,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None,
        }

    @staticmethod
    def from_row(row: tuple) -> 'Product':
        product = Product(
            id=row[0],
            name=row[1],
            price=row[2],
            stock=row[3],
            category_id=row[4],
            description=row[5] or '',
            image_url=row[6] or '',
        )
        product.created_at = row[7]
        product.updated_at = row[8]
        return product
