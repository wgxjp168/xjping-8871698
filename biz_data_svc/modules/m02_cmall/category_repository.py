"""
C端商城模块 — 分类 Repository
表：categories
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Category


class CategoryRepository(BaseRepository[Category]):
    """分类数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象实现                                              #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'categories'

    def _from_row(self, row) -> Category:
        return Category.from_row(tuple(row))

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, category: Category) -> Category:
        """新增分类，自动计算 level 和 path。"""
        if category.parent_id:
            parent = self.find_by_id(category.parent_id)
            if parent is None:
                raise ValueError(f'父分类 {category.parent_id} 不存在')
            level = parent.level + 1
            # path 临时占位，插入后用真实 id 更新
            parent_path = parent.path
        else:
            level = 1
            parent_path = '0'

        sql = """
            INSERT INTO categories
                (tenant_id, name, parent_id, icon_url, banner_url,
                 sort_order, level, path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._db.transaction():
            cur = self._db.execute(sql, (
                category.tenant_id,
                category.name,
                category.parent_id,
                category.icon_url,
                category.banner_url,
                category.sort_order,
                level,
                '',        # 占位，随后更新
                category.status,
            ))
            new_id = cur.lastrowid
            # 计算真实 path：parent_path/new_id
            path = f'{parent_path}/{new_id}'
            self._db.execute(
                'UPDATE categories SET path = ? WHERE id = ?',
                (path, new_id),
            )

        return self.find_by_id(new_id)

    def update(self, category: Category) -> bool:
        """更新分类基础信息（不重新计算 level/path）。"""
        sql = """
            UPDATE categories
            SET name=?, parent_id=?, icon_url=?, banner_url=?,
                sort_order=?, status=?
            WHERE id=?
        """
        cur = self._db.execute(sql, (
            category.name,
            category.parent_id,
            category.icon_url,
            category.banner_url,
            category.sort_order,
            category.status,
            category.id,
        ))
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, category_id: int) -> bool:
        """删除分类（调用方需自行确认无子分类/商品引用）。"""
        cur = self._db.execute(
            'DELETE FROM categories WHERE id = ?', (category_id,)
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_tenant(self, tenant_id: int) -> List[Category]:
        """查询租户下所有分类，按 sort_order、id 排序。"""
        return self._fetchall(
            'SELECT * FROM categories WHERE tenant_id=? ORDER BY sort_order, id',
            (tenant_id,),
        )

    def find_top_level(self, tenant_id: int) -> List[Category]:
        """查询顶级分类（parent_id IS NULL）。"""
        return self._fetchall(
            'SELECT * FROM categories WHERE tenant_id=? AND parent_id IS NULL '
            'ORDER BY sort_order, id',
            (tenant_id,),
        )

    def find_children(self, parent_id: int) -> List[Category]:
        """查询直接子分类。"""
        return self._fetchall(
            'SELECT * FROM categories WHERE parent_id=? ORDER BY sort_order, id',
            (parent_id,),
        )

    def find_by_id(self, id: int) -> Optional[Category]:
        """按主键查询。"""
        return self._fetchone(
            'SELECT * FROM categories WHERE id=?', (id,)
        )

    # ------------------------------------------------------------------ #
    #  树形结构                                                             #
    # ------------------------------------------------------------------ #

    def build_tree(self, tenant_id: int) -> List[dict]:
        """
        递归构建树形结构。
        返回顶级节点列表，每个节点含 'children' 键。
        """
        all_cats = self.find_by_tenant(tenant_id)
        # 索引：id -> dict
        nodes: Dict[int, dict] = {}
        for cat in all_cats:
            d = cat.to_dict()
            d['children'] = []
            nodes[cat.id] = d

        roots: List[dict] = []
        for cat in all_cats:
            node = nodes[cat.id]
            if cat.parent_id and cat.parent_id in nodes:
                nodes[cat.parent_id]['children'].append(node)
            else:
                roots.append(node)

        return roots
