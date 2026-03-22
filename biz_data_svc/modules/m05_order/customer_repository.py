from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Customer


class CustomerRepository(BaseRepository[Customer]):
    """客户数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'customers'

    def _from_row(self, row) -> Customer:
        return Customer.from_row(row)

    def add(self, customer: Customer) -> Customer:
        cur = self._db.execute(
            'INSERT INTO customers (tenant_id,user_id,name,phone,email) VALUES (?,?,?,?,?)',
            (customer.tenant_id, customer.user_id, customer.name,
             customer.phone, customer.email),
        )
        self._db.commit()
        customer.id = cur.lastrowid
        return customer

    def update(self, customer: Customer) -> bool:
        cur = self._db.execute(
            'UPDATE customers SET name=?,phone=?,email=? WHERE id=?',
            (customer.name, customer.phone, customer.email, customer.id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def find_by_tenant(self, tenant_id: int) -> List[Customer]:
        return self._fetchall(
            'SELECT * FROM customers WHERE tenant_id=? ORDER BY id', (tenant_id,))

    def find_by_phone(self, tenant_id: int, phone: str) -> Optional[Customer]:
        return self._fetchone(
            'SELECT * FROM customers WHERE tenant_id=? AND phone=?', (tenant_id, phone))

    def find_by_user(self, user_id: int) -> Optional[Customer]:
        return self._fetchone('SELECT * FROM customers WHERE user_id=?', (user_id,))
