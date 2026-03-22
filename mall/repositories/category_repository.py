import sqlite3
from typing import Optional, List
from ..models.category import Category


class CategoryRepository:
    """商品分类数据存储层 - 负责分类的增删改查操作"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, category: Category) -> Category:
        """新增分类，返回含 id 的 Category 对象"""
        sql = """
            INSERT INTO categories (name, description, parent_id)
            VALUES (?, ?, ?)
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (category.name, category.description, category.parent_id))
        self._conn.commit()
        category.id = cursor.lastrowid
        return category

    def update(self, category: Category) -> bool:
        """更新分类信息"""
        sql = """
            UPDATE categories
            SET name = ?, description = ?, parent_id = ?
            WHERE id = ?
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (
            category.name, category.description, category.parent_id, category.id,
        ))
        self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, category_id: int) -> bool:
        """删除分类（若有商品关联则会失败）"""
        cursor = self._conn.cursor()
        cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------ #
    #  读操作                                                               #
    # ------------------------------------------------------------------ #

    def find_by_id(self, category_id: int) -> Optional[Category]:
        """按 id 查找分类"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
        row = cursor.fetchone()
        return Category.from_row(tuple(row)) if row else None

    def find_by_name(self, name: str) -> Optional[Category]:
        """按名称查找分类"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE name = ?', (name,))
        row = cursor.fetchone()
        return Category.from_row(tuple(row)) if row else None

    def find_all(self) -> List[Category]:
        """查询所有分类"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM categories ORDER BY id')
        return [Category.from_row(tuple(row)) for row in cursor.fetchall()]

    def find_top_level(self) -> List[Category]:
        """查询所有顶级分类（无父分类）"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE parent_id IS NULL ORDER BY id')
        return [Category.from_row(tuple(row)) for row in cursor.fetchall()]

    def find_children(self, parent_id: int) -> List[Category]:
        """查询某分类的所有子分类"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT * FROM categories WHERE parent_id = ? ORDER BY id',
            (parent_id,),
        )
        return [Category.from_row(tuple(row)) for row in cursor.fetchall()]
