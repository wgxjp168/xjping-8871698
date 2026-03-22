"""
发票与对账模块 — 领域模型
所有模型均为 dataclass，提供 to_dict() 和 from_row() 方法。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
#  InvoiceItem                                                                 #
# --------------------------------------------------------------------------- #

@dataclass
class InvoiceItem:
    """发票明细行"""
    invoice_id: int
    product_name: str
    quantity: float
    unit_price: float
    amount: float
    tax_rate: float
    tax_amount: float
    id: Optional[int] = None
    spec: str = ''
    unit: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'product_name': self.product_name,
            'spec': self.spec,
            'unit': self.unit,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'amount': self.amount,
            'tax_rate': self.tax_rate,
            'tax_amount': self.tax_amount,
        }

    @staticmethod
    def from_row(row) -> 'InvoiceItem':
        """
        列顺序：id, invoice_id, product_name, spec, unit,
                quantity, unit_price, amount, tax_rate, tax_amount
        """
        r = tuple(row)
        return InvoiceItem(
            id=r[0],
            invoice_id=r[1],
            product_name=r[2],
            spec=r[3],
            unit=r[4],
            quantity=r[5],
            unit_price=r[6],
            amount=r[7],
            tax_rate=r[8],
            tax_amount=r[9],
        )


# --------------------------------------------------------------------------- #
#  Invoice                                                                     #
# --------------------------------------------------------------------------- #

@dataclass
class Invoice:
    """发票主表"""
    tenant_id: int
    invoice_no: str
    invoice_type: str
    direction: str           # in / out
    amount: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    buyer_name: str
    seller_name: str
    id: Optional[int] = None
    supplier_id: Optional[int] = None
    order_ids: Optional[str] = None
    issue_date: Optional[str] = None
    buyer_tax_no: str = ''
    seller_tax_no: str = ''
    status: str = 'pending'  # pending / verified / rejected / cancelled
    file_url: Optional[str] = None
    verified_by: Optional[int] = None
    verified_at: Optional[str] = None
    reject_reason: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    items: List[InvoiceItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'invoice_no': self.invoice_no,
            'invoice_type': self.invoice_type,
            'direction': self.direction,
            'supplier_id': self.supplier_id,
            'order_ids': self.order_ids,
            'amount': self.amount,
            'tax_rate': self.tax_rate,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
            'issue_date': self.issue_date,
            'buyer_name': self.buyer_name,
            'buyer_tax_no': self.buyer_tax_no,
            'seller_name': self.seller_name,
            'seller_tax_no': self.seller_tax_no,
            'status': self.status,
            'file_url': self.file_url,
            'verified_by': self.verified_by,
            'verified_at': self.verified_at,
            'reject_reason': self.reject_reason,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'items': [item.to_dict() for item in self.items],
        }

    @staticmethod
    def from_row(row) -> 'Invoice':
        """
        列顺序：id, tenant_id, invoice_no, invoice_type, direction,
                supplier_id, order_ids, amount, tax_rate, tax_amount,
                total_amount, issue_date, buyer_name, buyer_tax_no,
                seller_name, seller_tax_no, status, file_url,
                verified_by, verified_at, reject_reason, created_at, updated_at
        """
        r = tuple(row)
        return Invoice(
            id=r[0],
            tenant_id=r[1],
            invoice_no=r[2],
            invoice_type=r[3],
            direction=r[4],
            supplier_id=r[5],
            order_ids=r[6],
            amount=r[7],
            tax_rate=r[8],
            tax_amount=r[9],
            total_amount=r[10],
            issue_date=r[11],
            buyer_name=r[12],
            buyer_tax_no=r[13],
            seller_name=r[14],
            seller_tax_no=r[15],
            status=r[16],
            file_url=r[17],
            verified_by=r[18],
            verified_at=r[19],
            reject_reason=r[20],
            created_at=r[21],
            updated_at=r[22],
        )


# --------------------------------------------------------------------------- #
#  Reconciliation                                                              #
# --------------------------------------------------------------------------- #

@dataclass
class Reconciliation:
    """对账单"""
    tenant_id: int
    recon_no: str
    supplier_id: int
    period_start: str
    period_end: str
    order_amount: float
    invoice_amount: float
    id: Optional[int] = None
    diff_amount: float = 0.0
    status: str = 'draft'    # draft / sent / disputed / confirmed / closed
    supplier_confirmed: int = 0
    confirmed_at: Optional[str] = None
    note: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'recon_no': self.recon_no,
            'supplier_id': self.supplier_id,
            'period_start': self.period_start,
            'period_end': self.period_end,
            'order_amount': self.order_amount,
            'invoice_amount': self.invoice_amount,
            'diff_amount': self.diff_amount,
            'status': self.status,
            'supplier_confirmed': self.supplier_confirmed,
            'confirmed_at': self.confirmed_at,
            'note': self.note,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def from_row(row) -> 'Reconciliation':
        """
        列顺序：id, tenant_id, recon_no, supplier_id, period_start,
                period_end, order_amount, invoice_amount, diff_amount,
                status, supplier_confirmed, confirmed_at, note,
                created_by, created_at, updated_at
        """
        r = tuple(row)
        return Reconciliation(
            id=r[0],
            tenant_id=r[1],
            recon_no=r[2],
            supplier_id=r[3],
            period_start=r[4],
            period_end=r[5],
            order_amount=r[6],
            invoice_amount=r[7],
            diff_amount=r[8],
            status=r[9],
            supplier_confirmed=r[10],
            confirmed_at=r[11],
            note=r[12],
            created_by=r[13],
            created_at=r[14],
            updated_at=r[15],
        )


# --------------------------------------------------------------------------- #
#  Settlement                                                                  #
# --------------------------------------------------------------------------- #

@dataclass
class Settlement:
    """结算单"""
    tenant_id: int
    settle_no: str
    supplier_id: int
    amount: float
    payment_method: str
    id: Optional[int] = None
    reconciliation_id: Optional[int] = None
    invoice_ids: Optional[str] = None
    currency: str = 'CNY'
    bank_account: Optional[str] = None
    status: str = 'pending'  # pending / approved / rejected / paid / cancelled
    apply_at: Optional[str] = None
    approved_at: Optional[str] = None
    paid_at: Optional[str] = None
    approver_id: Optional[int] = None
    operator_id: Optional[int] = None
    note: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'settle_no': self.settle_no,
            'supplier_id': self.supplier_id,
            'reconciliation_id': self.reconciliation_id,
            'invoice_ids': self.invoice_ids,
            'amount': self.amount,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'bank_account': self.bank_account,
            'status': self.status,
            'apply_at': self.apply_at,
            'approved_at': self.approved_at,
            'paid_at': self.paid_at,
            'approver_id': self.approver_id,
            'operator_id': self.operator_id,
            'note': self.note,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def from_row(row) -> 'Settlement':
        """
        列顺序：id, tenant_id, settle_no, supplier_id, reconciliation_id,
                invoice_ids, amount, currency, payment_method, bank_account,
                status, apply_at, approved_at, paid_at, approver_id,
                operator_id, note, created_at, updated_at
        """
        r = tuple(row)
        return Settlement(
            id=r[0],
            tenant_id=r[1],
            settle_no=r[2],
            supplier_id=r[3],
            reconciliation_id=r[4],
            invoice_ids=r[5],
            amount=r[6],
            currency=r[7],
            payment_method=r[8],
            bank_account=r[9],
            status=r[10],
            apply_at=r[11],
            approved_at=r[12],
            paid_at=r[13],
            approver_id=r[14],
            operator_id=r[15],
            note=r[16],
            created_at=r[17],
            updated_at=r[18],
        )
