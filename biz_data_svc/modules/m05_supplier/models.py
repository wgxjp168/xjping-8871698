"""
供应商模块 — 领域模型
涉及表：suppliers, supplier_qualifications, supplier_quotes,
        supplier_scores, supplier_risks
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


# --------------------------------------------------------------------------- #
#  Supplier                                                                    #
# --------------------------------------------------------------------------- #

@dataclass
class Supplier:
    """供应商主表"""
    tenant_id: int
    name: str
    code: str
    id: Optional[int] = None
    short_name: str = ''
    supplier_type: str = 'general'
    status: str = 'pending'         # pending / active / blacklisted / suspended
    contact_name: str = ''
    phone: str = ''
    email: str = ''
    address: str = ''
    website: str = ''
    tax_no: str = ''
    bank_account: str = ''
    bank_name: str = ''
    payment_terms: str = ''
    credit_limit: float = 0.0
    reviewer_id: Optional[int] = None
    reviewed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'code': self.code,
            'short_name': self.short_name,
            'supplier_type': self.supplier_type,
            'status': self.status,
            'contact_name': self.contact_name,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'website': self.website,
            'tax_no': self.tax_no,
            'bank_account': self.bank_account,
            'bank_name': self.bank_name,
            'payment_terms': self.payment_terms,
            'credit_limit': self.credit_limit,
            'reviewer_id': self.reviewer_id,
            'reviewed_at': self.reviewed_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def from_row(row) -> 'Supplier':
        """
        列顺序：id,tenant_id,name,code,short_name,supplier_type,status,
                contact_name,phone,email,address,website,tax_no,
                bank_account,bank_name,payment_terms,credit_limit,
                reviewer_id,reviewed_at,created_at,updated_at
        """
        r = tuple(row)
        return Supplier(
            id=r[0],
            tenant_id=r[1],
            name=r[2],
            code=r[3],
            short_name=r[4],
            supplier_type=r[5],
            status=r[6],
            contact_name=r[7],
            phone=r[8],
            email=r[9],
            address=r[10],
            website=r[11],
            tax_no=r[12],
            bank_account=r[13],
            bank_name=r[14],
            payment_terms=r[15],
            credit_limit=r[16],
            reviewer_id=r[17],
            reviewed_at=r[18],
            created_at=r[19],
            updated_at=r[20],
        )


# --------------------------------------------------------------------------- #
#  SupplierQualification                                                       #
# --------------------------------------------------------------------------- #

@dataclass
class SupplierQualification:
    """供应商资质证书"""
    supplier_id: int
    qual_type: str
    name: str
    issue_org: str
    id: Optional[int] = None
    issue_date: Optional[str] = None
    expire_date: Optional[str] = None
    file_url: str = ''
    status: str = 'valid'           # valid / expired / revoked
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'qual_type': self.qual_type,
            'name': self.name,
            'issue_org': self.issue_org,
            'issue_date': self.issue_date,
            'expire_date': self.expire_date,
            'file_url': self.file_url,
            'status': self.status,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'SupplierQualification':
        """
        列顺序：id,supplier_id,qual_type,name,issue_org,issue_date,
                expire_date,file_url,status,created_at
        """
        r = tuple(row)
        return SupplierQualification(
            id=r[0],
            supplier_id=r[1],
            qual_type=r[2],
            name=r[3],
            issue_org=r[4],
            issue_date=r[5],
            expire_date=r[6],
            file_url=r[7],
            status=r[8],
            created_at=r[9],
        )


# --------------------------------------------------------------------------- #
#  SupplierQuote                                                               #
# --------------------------------------------------------------------------- #

@dataclass
class SupplierQuote:
    """供应商报价单（目录价）"""
    supplier_id: int
    tenant_id: int
    product_name: str
    unit: str
    unit_price: float
    min_qty: float
    delivery_days: int
    id: Optional[int] = None
    spec: str = ''
    currency: str = 'CNY'
    valid_until: Optional[str] = None
    status: str = 'active'          # active / withdrawn / expired
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'tenant_id': self.tenant_id,
            'product_name': self.product_name,
            'spec': self.spec,
            'unit': self.unit,
            'unit_price': self.unit_price,
            'currency': self.currency,
            'min_qty': self.min_qty,
            'delivery_days': self.delivery_days,
            'valid_until': self.valid_until,
            'status': self.status,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'SupplierQuote':
        """
        列顺序：id,supplier_id,tenant_id,product_name,spec,unit,
                unit_price,currency,min_qty,delivery_days,
                valid_until,status,created_at
        """
        r = tuple(row)
        return SupplierQuote(
            id=r[0],
            supplier_id=r[1],
            tenant_id=r[2],
            product_name=r[3],
            spec=r[4],
            unit=r[5],
            unit_price=r[6],
            currency=r[7],
            min_qty=r[8],
            delivery_days=r[9],
            valid_until=r[10],
            status=r[11],
            created_at=r[12],
        )


# --------------------------------------------------------------------------- #
#  SupplierScore                                                               #
# --------------------------------------------------------------------------- #

@dataclass
class SupplierScore:
    """供应商绩效评分"""
    supplier_id: int
    tenant_id: int
    period: str             # 如 '2024-Q1'
    quality_score: float
    delivery_score: float
    price_score: float
    service_score: float
    evaluator_id: int
    id: Optional[int] = None
    total_score: float = 0.0
    level: str = ''         # S/A/B/C/D
    note: str = ''
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'tenant_id': self.tenant_id,
            'period': self.period,
            'quality_score': self.quality_score,
            'delivery_score': self.delivery_score,
            'price_score': self.price_score,
            'service_score': self.service_score,
            'total_score': self.total_score,
            'level': self.level,
            'evaluator_id': self.evaluator_id,
            'note': self.note,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'SupplierScore':
        """
        列顺序：id,supplier_id,tenant_id,period,quality_score,
                delivery_score,price_score,service_score,total_score,
                level,evaluator_id,note,created_at
        """
        r = tuple(row)
        return SupplierScore(
            id=r[0],
            supplier_id=r[1],
            tenant_id=r[2],
            period=r[3],
            quality_score=r[4],
            delivery_score=r[5],
            price_score=r[6],
            service_score=r[7],
            total_score=r[8],
            level=r[9],
            evaluator_id=r[10],
            note=r[11],
            created_at=r[12],
        )


# --------------------------------------------------------------------------- #
#  SupplierRisk                                                                #
# --------------------------------------------------------------------------- #

@dataclass
class SupplierRisk:
    """供应商风险记录"""
    supplier_id: int
    risk_type: str
    level: str              # low / medium / high / critical
    description: str
    id: Optional[int] = None
    source: str = ''
    status: str = 'open'    # open / mitigating / resolved
    found_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolver_id: Optional[int] = None
    resolution_note: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'risk_type': self.risk_type,
            'level': self.level,
            'description': self.description,
            'source': self.source,
            'status': self.status,
            'found_at': self.found_at,
            'resolved_at': self.resolved_at,
            'resolver_id': self.resolver_id,
            'resolution_note': self.resolution_note,
        }

    @staticmethod
    def from_row(row) -> 'SupplierRisk':
        """
        列顺序：id,supplier_id,risk_type,level,description,source,
                status,found_at,resolved_at,resolver_id,resolution_note
        """
        r = tuple(row)
        return SupplierRisk(
            id=r[0],
            supplier_id=r[1],
            risk_type=r[2],
            level=r[3],
            description=r[4],
            source=r[5],
            status=r[6],
            found_at=r[7],
            resolved_at=r[8],
            resolver_id=r[9],
            resolution_note=r[10],
        )
