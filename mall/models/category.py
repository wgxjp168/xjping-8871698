from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    """商品分类模型"""
    name: str
    description: str = ''
    parent_id: Optional[int] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
        }

    @staticmethod
    def from_row(row: tuple) -> 'Category':
        return Category(
            id=row[0],
            name=row[1],
            description=row[2] or '',
            parent_id=row[3],
        )
