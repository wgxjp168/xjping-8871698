from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Category, Brand


class CategoryRepository(BaseRepository[Category]):
    """类目数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'categories'

    def _from_row(self, row) -> Category:
        return Category.from_row(row)

    def add(self, category: Category) -> Category:
        cur = self._db.execute(
            'INSERT INTO categories (tenant_id,name,parent_id,sort_order) VALUES (?,?,?,?)',
            (category.tenant_id, category.name, category.parent_id, category.sort_order),
        )
        self._db.commit()
        category.id = cur.lastrowid
        return category

    def update(self, category: Category) -> bool:
        cur = self._db.execute(
            'UPDATE categories SET name=?,parent_id=?,sort_order=? WHERE id=?',
            (category.name, category.parent_id, category.sort_order, category.id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def find_by_tenant(self, tenant_id: int) -> List[Category]:
        return self._fetchall(
            'SELECT * FROM categories WHERE tenant_id=? ORDER BY sort_order,id', (tenant_id,))

    def find_top_level(self, tenant_id: int) -> List[Category]:
        return self._fetchall(
            'SELECT * FROM categories WHERE tenant_id=? AND parent_id IS NULL ORDER BY sort_order',
            (tenant_id,),
        )

    def find_children(self, parent_id: int) -> List[Category]:
        return self._fetchall(
            'SELECT * FROM categories WHERE parent_id=? ORDER BY sort_order', (parent_id,))

    # ---- 品牌 ----

    def add_brand(self, brand: Brand) -> Brand:
        cur = self._db.execute(
            'INSERT INTO brands (tenant_id,name,logo_url) VALUES (?,?,?)',
            (brand.tenant_id, brand.name, brand.logo_url),
        )
        self._db.commit()
        brand.id = cur.lastrowid
        return brand

    def find_brands(self, tenant_id: int) -> List[Brand]:
        rows = self._db.execute(
            'SELECT * FROM brands WHERE tenant_id=? ORDER BY name', (tenant_id,)).fetchall()
        return [Brand.from_row(r) for r in rows]
