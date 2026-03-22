"""
发票 Repository
继承 BaseRepository[Invoice]，提供 invoices 及 invoice_items 表完整操作。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Invoice, InvoiceItem


class InvoiceRepository(BaseRepository[Invoice]):
    """invoices 表（及 invoice_items 表）的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'invoices'

    def _from_row(self, row) -> Invoice:
        return Invoice.from_row(row)

    # ------------------------------------------------------------------ #
    #  工具方法                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def calculate_tax(amount: float, tax_rate: float) -> float:
        """计算税额：amount * tax_rate（tax_rate 为小数，如 0.13 表示 13%）"""
        return round(amount * tax_rate, 2)

    def _load_items(self, invoice_id: int) -> List[InvoiceItem]:
        """加载指定发票的所有明细行"""
        rows = self._db.execute(
            'SELECT * FROM invoice_items WHERE invoice_id = ? ORDER BY id',
            (invoice_id,),
        ).fetchall()
        return [InvoiceItem.from_row(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def create(self, invoice: Invoice) -> Invoice:
        """
        事务中插入发票主表及明细行。
        返回带 id 及 items 的 Invoice 对象。
        """
        sql_invoice = '''
            INSERT INTO invoices
                (tenant_id, invoice_no, invoice_type, direction, supplier_id,
                 order_ids, amount, tax_rate, tax_amount, total_amount,
                 issue_date, buyer_name, buyer_tax_no, seller_name, seller_tax_no,
                 status, file_url, verified_by, verified_at, reject_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        sql_item = '''
            INSERT INTO invoice_items
                (invoice_id, product_name, spec, unit, quantity,
                 unit_price, amount, tax_rate, tax_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        with self._db.transaction():
            cur = self._db.execute(sql_invoice, (
                invoice.tenant_id,
                invoice.invoice_no,
                invoice.invoice_type,
                invoice.direction,
                invoice.supplier_id,
                invoice.order_ids,
                invoice.amount,
                invoice.tax_rate,
                invoice.tax_amount,
                invoice.total_amount,
                invoice.issue_date,
                invoice.buyer_name,
                invoice.buyer_tax_no,
                invoice.seller_name,
                invoice.seller_tax_no,
                invoice.status,
                invoice.file_url,
                invoice.verified_by,
                invoice.verified_at,
                invoice.reject_reason,
            ))
            invoice.id = cur.lastrowid

            if invoice.items:
                item_params = [
                    (
                        invoice.id,
                        item.product_name,
                        item.spec,
                        item.unit,
                        item.quantity,
                        item.unit_price,
                        item.amount,
                        item.tax_rate,
                        item.tax_amount,
                    )
                    for item in invoice.items
                ]
                self._db.executemany(sql_item, item_params)

        # 回填 item id
        invoice.items = self._load_items(invoice.id)
        return invoice

    def verify(self, invoice_id: int, verifier_id: int) -> bool:
        """审核通过：status=verified, verified_by, verified_at=now"""
        cur = self._db.execute(
            '''UPDATE invoices
               SET status = 'verified',
                   verified_by = ?,
                   verified_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (verifier_id, invoice_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def reject(self, invoice_id: int, verifier_id: int, reason: str) -> bool:
        """审核拒绝：status=rejected, verified_by, reject_reason"""
        cur = self._db.execute(
            '''UPDATE invoices
               SET status = 'rejected',
                   verified_by = ?,
                   reject_reason = ?
               WHERE id = ?''',
            (verifier_id, reason, invoice_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def cancel(self, invoice_id: int) -> bool:
        """作废发票：status=cancelled"""
        cur = self._db.execute(
            "UPDATE invoices SET status = 'cancelled' WHERE id = ?",
            (invoice_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[Invoice]:  # noqa: A002
        """按主键查询发票，附带明细行"""
        invoice = self._fetchone(
            'SELECT * FROM invoices WHERE id = ?', (id,)
        )
        if invoice:
            invoice.items = self._load_items(invoice.id)
        return invoice

    def find_by_tenant(
        self,
        tenant_id: int,
        direction: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Invoice]:
        """按租户查询发票列表，可选 direction / status 过滤"""
        sql = 'SELECT * FROM invoices WHERE tenant_id = ?'
        params: list = [tenant_id]
        if direction is not None:
            sql += ' AND direction = ?'
            params.append(direction)
        if status is not None:
            sql += ' AND status = ?'
            params.append(status)
        sql += ' ORDER BY id'
        rows = self._db.execute(sql, tuple(params)).fetchall()
        invoices = [Invoice.from_row(r) for r in rows]
        for inv in invoices:
            inv.items = self._load_items(inv.id)
        return invoices

    def find_by_supplier(self, supplier_id: int) -> List[Invoice]:
        """按供应商查询发票列表"""
        rows = self._db.execute(
            'SELECT * FROM invoices WHERE supplier_id = ? ORDER BY id',
            (supplier_id,),
        ).fetchall()
        invoices = [Invoice.from_row(r) for r in rows]
        for inv in invoices:
            inv.items = self._load_items(inv.id)
        return invoices

    def find_by_invoice_no(self, invoice_no: str) -> Optional[Invoice]:
        """按发票号查询"""
        invoice = self._fetchone(
            'SELECT * FROM invoices WHERE invoice_no = ?', (invoice_no,)
        )
        if invoice:
            invoice.items = self._load_items(invoice.id)
        return invoice
