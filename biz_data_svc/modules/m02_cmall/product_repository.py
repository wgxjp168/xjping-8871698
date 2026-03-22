"""
C端商城模块 — 商品 Repository
表：products
集成：
  - Redis 热点商品缓存（读缓存 + 写失效）
  - Elasticsearch 商品索引（写同步）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Product


class ProductRepository(BaseRepository[Product]):
    """商品数据访问层（含 Redis 缓存 + ES 索引集成）"""

    def __init__(self, db: Database,
                 redis_client=None,
                 es_client=None):
        super().__init__(db)
        self._redis = redis_client   # infra.RedisClient，可为 None（降级）
        self._es    = es_client      # infra.ESClient，可为 None（降级）

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象实现                                              #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'products'

    def _from_row(self, row) -> Product:
        return Product.from_row(tuple(row))

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, product: Product) -> Product:
        """新增商品，返回带自增 id 的对象，并同步写入 ES 索引。"""
        sql = """
            INSERT INTO products
                (tenant_id, category_id, supplier_id, name, subtitle,
                 description, cover_image, unit, weight, status,
                 is_featured, tags, sales_count, view_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cur = self._db.execute(sql, (
            product.tenant_id,
            product.category_id,
            product.supplier_id,
            product.name,
            product.subtitle,
            product.description,
            product.cover_image,
            product.unit,
            product.weight,
            product.status,
            int(product.is_featured),
            product.tags,
            product.sales_count,
            product.view_count,
        ))
        self._db.commit()
        saved = self.find_by_id(cur.lastrowid)
        # 同步写入 Elasticsearch
        if saved and self._es:
            self._es.index_product(saved.to_dict())
        return saved

    def update(self, product: Product) -> bool:
        """更新商品完整信息，并失效 Redis 缓存 + 同步 ES。"""
        sql = """
            UPDATE products
            SET category_id=?, supplier_id=?, name=?, subtitle=?,
                description=?, cover_image=?, unit=?, weight=?,
                status=?, is_featured=?, tags=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """
        cur = self._db.execute(sql, (
            product.category_id,
            product.supplier_id,
            product.name,
            product.subtitle,
            product.description,
            product.cover_image,
            product.unit,
            product.weight,
            product.status,
            int(product.is_featured),
            product.tags,
            product.id,
        ))
        self._db.commit()
        if cur.rowcount > 0:
            self._invalidate_cache(product.id)
            if self._es:
                self._es.index_product(product.to_dict())
        return cur.rowcount > 0

    def update_status(self, product_id: int, status: str) -> bool:
        """更新商品上架/下架状态，并失效 Redis 缓存 + 同步 ES。"""
        cur = self._db.execute(
            'UPDATE products SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (status, product_id),
        )
        self._db.commit()
        if cur.rowcount > 0:
            self._invalidate_cache(product_id)
            updated = self.find_by_id(product_id)
            if updated and self._es:
                self._es.index_product(updated.to_dict())
        return cur.rowcount > 0

    def increment_view(self, product_id: int) -> bool:
        """浏览量 +1（原子自增），不失效缓存（允许短暂不一致）。"""
        cur = self._db.execute(
            'UPDATE products SET view_count = view_count + 1 WHERE id=?',
            (product_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, product_id: int) -> bool:
        """删除商品，并失效 Redis 缓存 + 从 ES 索引移除。"""
        cur = self._db.execute(
            'DELETE FROM products WHERE id=?', (product_id,)
        )
        self._db.commit()
        if cur.rowcount > 0:
            self._invalidate_cache(product_id)
            if self._es:
                self._es.delete_product(product_id)
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  缓存辅助                                                            #
    # ------------------------------------------------------------------ #

    def _invalidate_cache(self, product_id: int) -> None:
        """主动失效 Redis 商品缓存。"""
        if self._redis:
            self._redis.invalidate_product(product_id)

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[Product]:
        """
        先查 Redis 缓存，未命中再查 SQLite/MySQL，并回填缓存。
        """
        # 1. 读缓存
        if self._redis:
            cached = self._redis.get_product(id)
            if cached is not None:
                return Product.from_dict(cached)
        # 2. 读数据库
        product = self._fetchone('SELECT * FROM products WHERE id=?', (id,))
        # 3. 回填缓存
        if product and self._redis:
            self._redis.cache_product(id, product.to_dict())
        return product

    def find_by_tenant(self, tenant_id: int,
                       status: Optional[str] = None) -> List[Product]:
        """查询租户下商品，可按 status 过滤。"""
        if status is not None:
            return self._fetchall(
                'SELECT * FROM products WHERE tenant_id=? AND status=? '
                'ORDER BY id DESC',
                (tenant_id, status),
            )
        return self._fetchall(
            'SELECT * FROM products WHERE tenant_id=? ORDER BY id DESC',
            (tenant_id,),
        )

    def find_by_category(self, category_id: int,
                         status: str = 'on_sale') -> List[Product]:
        """查询指定分类下的商品，默认仅返回在售品。"""
        return self._fetchall(
            'SELECT * FROM products WHERE category_id=? AND status=? '
            'ORDER BY sales_count DESC, id DESC',
            (category_id, status),
        )

    def search(self, tenant_id: int, keyword: str,
               page: int = 1, size: int = 20) -> Tuple[List[Product], int]:
        """
        全文关键词搜索（name / subtitle / tags LIKE）。
        返回 (items, total)，page 从 1 开始。
        """
        like = f'%{keyword}%'
        where = (
            'tenant_id=? AND (name LIKE ? OR subtitle LIKE ? OR tags LIKE ?)'
        )
        params: tuple = (tenant_id, like, like, like)

        total = self._scalar(
            f'SELECT COUNT(*) FROM {self.table} WHERE {where}', params
        ) or 0

        offset = (page - 1) * size
        items = self._fetchall(
            f'SELECT * FROM {self.table} WHERE {where} '
            f'ORDER BY sales_count DESC, id DESC LIMIT ? OFFSET ?',
            params + (size, offset),
        )
        return items, total

    def find_featured(self, tenant_id: int) -> List[Product]:
        """查询推荐/精选商品。"""
        return self._fetchall(
            'SELECT * FROM products WHERE tenant_id=? AND is_featured=1 '
            'AND status=? ORDER BY sales_count DESC',
            (tenant_id, 'on_sale'),
        )
