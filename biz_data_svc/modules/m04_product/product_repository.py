from typing import List, Optional, Tuple
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Product


class ProductRepository(BaseRepository[Product]):
    """商品数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'products'

    def _from_row(self, row) -> Product:
        return Product.from_row(row)

    # ---- 写 ----

    def add(self, product: Product) -> Product:
        cur = self._db.execute(
            '''INSERT INTO products
               (tenant_id,category_id,brand_id,name,sku,barcode,unit,
                cost_price,sale_price,description,image_url,status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (product.tenant_id, product.category_id, product.brand_id,
             product.name, product.sku, product.barcode, product.unit,
             product.cost_price, product.sale_price, product.description,
             product.image_url, product.status),
        )
        self._db.commit()
        product.id = cur.lastrowid
        return product

    def update(self, product: Product) -> bool:
        cur = self._db.execute(
            '''UPDATE products
               SET category_id=?,brand_id=?,name=?,barcode=?,unit=?,
                   cost_price=?,sale_price=?,description=?,image_url=?,
                   updated_at=CURRENT_TIMESTAMP
               WHERE id=?''',
            (product.category_id, product.brand_id, product.name,
             product.barcode, product.unit, product.cost_price,
             product.sale_price, product.description, product.image_url, product.id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def update_status(self, product_id: int, status: str) -> bool:
        cur = self._db.execute(
            'UPDATE products SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (status, product_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def update_price(self, product_id: int, sale_price: float) -> bool:
        cur = self._db.execute(
            'UPDATE products SET sale_price=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (sale_price, product_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ---- 读 ----

    def find_by_tenant(self, tenant_id: int) -> List[Product]:
        return self._fetchall(
            'SELECT * FROM products WHERE tenant_id=? ORDER BY id', (tenant_id,))

    def find_by_category(self, category_id: int) -> List[Product]:
        return self._fetchall(
            "SELECT * FROM products WHERE category_id=? AND status='on_sale' ORDER BY id",
            (category_id,),
        )

    def find_by_sku(self, tenant_id: int, sku: str) -> Optional[Product]:
        return self._fetchone(
            'SELECT * FROM products WHERE tenant_id=? AND sku=?', (tenant_id, sku))

    def search(self, tenant_id: int, keyword: str) -> List[Product]:
        return self._fetchall(
            "SELECT * FROM products WHERE tenant_id=? AND name LIKE ? AND status='on_sale' ORDER BY id",
            (tenant_id, f'%{keyword}%'),
        )

    def find_by_price_range(self, tenant_id: int, min_p: float, max_p: float) -> List[Product]:
        return self._fetchall(
            '''SELECT * FROM products WHERE tenant_id=? AND sale_price BETWEEN ? AND ?
               AND status='on_sale' ORDER BY sale_price''',
            (tenant_id, min_p, max_p),
        )

    def find_by_brand(self, brand_id: int) -> List[Product]:
        return self._fetchall(
            "SELECT * FROM products WHERE brand_id=? AND status='on_sale' ORDER BY id",
            (brand_id,),
        )

    def paginate_by_tenant(self, tenant_id: int, page: int = 1,
                           size: int = 20) -> Tuple[List[Product], int]:
        return self.paginate(page, size, 'tenant_id=?', (tenant_id,))
