"""
订单交易模块 — 领域模型
所有模型均为 dataclass，提供 to_dict() 和 from_row() 方法。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
#  OrderItem                                                                   #
# --------------------------------------------------------------------------- #

@dataclass
class OrderItem:
    """订单明细行"""
    order_id: int
    product_id: int
    sku_id: int
    product_name: str
    sku_attrs: str                  # JSON 字符串
    quantity: int
    unit_price: float
    subtotal: float
    id: Optional[int] = None
    refund_qty: int = 0
    refund_amount: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'sku_id': self.sku_id,
            'product_name': self.product_name,
            'sku_attrs': self.sku_attrs,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'subtotal': self.subtotal,
            'refund_qty': self.refund_qty,
            'refund_amount': self.refund_amount,
        }

    @staticmethod
    def from_row(row) -> 'OrderItem':
        """
        列顺序：id, order_id, product_id, sku_id, product_name,
                sku_attrs, quantity, unit_price, subtotal,
                refund_qty, refund_amount
        """
        r = tuple(row)
        return OrderItem(
            id=r[0],
            order_id=r[1],
            product_id=r[2],
            sku_id=r[3],
            product_name=r[4],
            sku_attrs=r[5],
            quantity=r[6],
            unit_price=r[7],
            subtotal=r[8],
            refund_qty=r[9],
            refund_amount=r[10],
        )


# --------------------------------------------------------------------------- #
#  Order                                                                       #
# --------------------------------------------------------------------------- #

@dataclass
class Order:
    """订单主表"""
    tenant_id: int
    order_no: str
    user_id: int
    receiver_name: str
    receiver_phone: str
    total_amount: float
    pay_amount: float
    id: Optional[int] = None
    province: str = ''
    city: str = ''
    district: str = ''
    address_detail: str = ''
    status: str = 'pending'         # pending/paid/shipped/completed/cancelled
    discount_amount: float = 0.0
    shipping_fee: float = 0.0
    payment_method: str = ''
    paid_at: Optional[str] = None
    remark: str = ''
    cancel_reason: str = ''
    source: str = 'pc'              # pc/ios/android/mini_program/api
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    items: List[OrderItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'order_no': self.order_no,
            'user_id': self.user_id,
            'receiver_name': self.receiver_name,
            'receiver_phone': self.receiver_phone,
            'province': self.province,
            'city': self.city,
            'district': self.district,
            'address_detail': self.address_detail,
            'status': self.status,
            'total_amount': self.total_amount,
            'discount_amount': self.discount_amount,
            'shipping_fee': self.shipping_fee,
            'pay_amount': self.pay_amount,
            'payment_method': self.payment_method,
            'paid_at': self.paid_at,
            'remark': self.remark,
            'cancel_reason': self.cancel_reason,
            'source': self.source,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'items': [item.to_dict() for item in self.items],
        }

    @staticmethod
    def from_row(row) -> 'Order':
        """
        列顺序：id, tenant_id, order_no, user_id,
                receiver_name, receiver_phone,
                province, city, district, address_detail,
                status, total_amount, discount_amount, shipping_fee, pay_amount,
                payment_method, paid_at, remark, cancel_reason, source,
                created_at, updated_at
        """
        r = tuple(row)
        return Order(
            id=r[0],
            tenant_id=r[1],
            order_no=r[2],
            user_id=r[3],
            receiver_name=r[4],
            receiver_phone=r[5],
            province=r[6],
            city=r[7],
            district=r[8],
            address_detail=r[9],
            status=r[10],
            total_amount=r[11],
            discount_amount=r[12],
            shipping_fee=r[13],
            pay_amount=r[14],
            payment_method=r[15],
            paid_at=r[16],
            remark=r[17],
            cancel_reason=r[18],
            source=r[19],
            created_at=r[20],
            updated_at=r[21],
        )


# --------------------------------------------------------------------------- #
#  Payment                                                                     #
# --------------------------------------------------------------------------- #

@dataclass
class Payment:
    """支付记录"""
    order_id: int
    payment_no: str
    amount: float
    method: str                     # alipay/wechat/bank_card/...
    id: Optional[int] = None
    channel_no: str = ''            # 第三方支付流水号
    status: str = 'pending'         # pending/success/failed/cancelled
    paid_at: Optional[str] = None
    expired_at: Optional[str] = None
    extra: str = ''                 # JSON 扩展字段
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'order_id': self.order_id,
            'payment_no': self.payment_no,
            'amount': self.amount,
            'method': self.method,
            'channel_no': self.channel_no,
            'status': self.status,
            'paid_at': self.paid_at,
            'expired_at': self.expired_at,
            'extra': self.extra,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'Payment':
        """
        列顺序：id, order_id, payment_no, amount, method,
                channel_no, status, paid_at, expired_at, extra, created_at
        """
        r = tuple(row)
        return Payment(
            id=r[0],
            order_id=r[1],
            payment_no=r[2],
            amount=r[3],
            method=r[4],
            channel_no=r[5],
            status=r[6],
            paid_at=r[7],
            expired_at=r[8],
            extra=r[9],
            created_at=r[10],
        )


# --------------------------------------------------------------------------- #
#  Refund                                                                      #
# --------------------------------------------------------------------------- #

@dataclass
class Refund:
    """退款申请"""
    order_id: int
    refund_no: str
    amount: float
    reason: str
    id: Optional[int] = None
    payment_id: Optional[int] = None
    refund_type: str = 'refund_only'  # refund_only / return_refund
    images: str = ''                # JSON 数组，凭证图片 URL
    status: str = 'pending'         # pending/approved/rejected/processing/completed/cancelled
    reject_reason: str = ''
    apply_at: Optional[str] = None
    approve_at: Optional[str] = None
    complete_at: Optional[str] = None
    operator_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'order_id': self.order_id,
            'payment_id': self.payment_id,
            'refund_no': self.refund_no,
            'amount': self.amount,
            'refund_type': self.refund_type,
            'reason': self.reason,
            'images': self.images,
            'status': self.status,
            'reject_reason': self.reject_reason,
            'apply_at': self.apply_at,
            'approve_at': self.approve_at,
            'complete_at': self.complete_at,
            'operator_id': self.operator_id,
        }

    @staticmethod
    def from_row(row) -> 'Refund':
        """
        列顺序：id, order_id, payment_id, refund_no, amount,
                refund_type, reason, images, status, reject_reason,
                apply_at, approve_at, complete_at, operator_id
        """
        r = tuple(row)
        return Refund(
            id=r[0],
            order_id=r[1],
            payment_id=r[2],
            refund_no=r[3],
            amount=r[4],
            refund_type=r[5],
            reason=r[6],
            images=r[7],
            status=r[8],
            reject_reason=r[9],
            apply_at=r[10],
            approve_at=r[11],
            complete_at=r[12],
            operator_id=r[13],
        )


# --------------------------------------------------------------------------- #
#  Logistics                                                                   #
# --------------------------------------------------------------------------- #

@dataclass
class Logistics:
    """物流信息"""
    order_id: int
    company: str                    # 快递公司名称
    company_code: str               # 快递公司编码
    tracking_no: str                # 运单号
    id: Optional[int] = None
    status: str = 'pending'         # pending/shipped/in_transit/delivered
    signed_at: Optional[str] = None
    receiver: str = ''              # 签收人
    traces: str = '[]'             # JSON 数组，物流轨迹
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'order_id': self.order_id,
            'company': self.company,
            'company_code': self.company_code,
            'tracking_no': self.tracking_no,
            'status': self.status,
            'signed_at': self.signed_at,
            'receiver': self.receiver,
            'traces': self.traces,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def from_row(row) -> 'Logistics':
        """
        列顺序：id, order_id, company, company_code, tracking_no,
                status, signed_at, receiver, traces, created_at, updated_at
        """
        r = tuple(row)
        return Logistics(
            id=r[0],
            order_id=r[1],
            company=r[2],
            company_code=r[3],
            tracking_no=r[4],
            status=r[5],
            signed_at=r[6],
            receiver=r[7],
            traces=r[8],
            created_at=r[9],
            updated_at=r[10],
        )
