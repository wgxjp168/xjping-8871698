"""
C端商城模块 — 收货地址 Repository
表：delivery_addresses
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import DeliveryAddress


class AddressRepository(BaseRepository[DeliveryAddress]):
    """收货地址数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象实现                                              #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'delivery_addresses'

    def _from_row(self, row) -> DeliveryAddress:
        return DeliveryAddress.from_row(tuple(row))

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, address: DeliveryAddress) -> DeliveryAddress:
        """
        新增收货地址。
        若 is_default=True，先将该用户其他地址的默认标记清除，
        再插入新地址，整个过程在事务中完成。
        """
        sql = """
            INSERT INTO delivery_addresses
                (user_id, receiver_name, phone, province, city,
                 district, street, address_detail, postal_code,
                 is_default, tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._db.transaction():
            if address.is_default:
                self._db.execute(
                    'UPDATE delivery_addresses SET is_default=0 WHERE user_id=?',
                    (address.user_id,),
                )
            cur = self._db.execute(sql, (
                address.user_id,
                address.receiver_name,
                address.phone,
                address.province,
                address.city,
                address.district,
                address.street,
                address.address_detail,
                address.postal_code,
                int(address.is_default),
                address.tag,
            ))
            new_id = cur.lastrowid

        return self.find_by_id(new_id)

    def update(self, address: DeliveryAddress) -> bool:
        """更新收货地址信息（不含 is_default，用 set_default 方法管理）。"""
        sql = """
            UPDATE delivery_addresses
            SET receiver_name=?, phone=?, province=?, city=?, district=?,
                street=?, address_detail=?, postal_code=?, tag=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND user_id=?
        """
        cur = self._db.execute(sql, (
            address.receiver_name,
            address.phone,
            address.province,
            address.city,
            address.district,
            address.street,
            address.address_detail,
            address.postal_code,
            address.tag,
            address.id,
            address.user_id,
        ))
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, address_id: int, user_id: int) -> bool:
        """
        删除收货地址。
        同时验证归属用户，防止越权删除。
        """
        cur = self._db.execute(
            'DELETE FROM delivery_addresses WHERE id=? AND user_id=?',
            (address_id, user_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def set_default(self, address_id: int, user_id: int) -> bool:
        """
        设置默认收货地址（事务）：
        1. 先清除该用户所有默认标记；
        2. 再设置指定地址为默认。
        """
        with self._db.transaction():
            self._db.execute(
                'UPDATE delivery_addresses SET is_default=0 WHERE user_id=?',
                (user_id,),
            )
            cur = self._db.execute(
                """
                UPDATE delivery_addresses
                SET is_default=1, updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND user_id=?
                """,
                (address_id, user_id),
            )
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_user(self, user_id: int) -> List[DeliveryAddress]:
        """
        查询用户所有收货地址。
        默认地址排在最前，其余按创建时间倒序。
        """
        return self._fetchall(
            'SELECT * FROM delivery_addresses WHERE user_id=? '
            'ORDER BY is_default DESC, created_at DESC',
            (user_id,),
        )

    def find_default(self, user_id: int) -> Optional[DeliveryAddress]:
        """查询用户的默认收货地址。"""
        return self._fetchone(
            'SELECT * FROM delivery_addresses WHERE user_id=? AND is_default=1',
            (user_id,),
        )

    def find_by_id(self, id: int) -> Optional[DeliveryAddress]:
        """按主键查询收货地址。"""
        return self._fetchone(
            'SELECT * FROM delivery_addresses WHERE id=?', (id,)
        )
