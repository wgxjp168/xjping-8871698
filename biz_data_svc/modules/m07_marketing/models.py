from dataclasses import dataclass
from typing import Optional


@dataclass
class Promotion:
    tenant_id:     int
    name:          str
    promo_type:    str            # discount / full_reduce / gift / flash_sale
    start_at:      str
    end_at:        str
    discount_rate: float = 1.0   # 折扣率，1.0=不折扣
    reduce_amount: float = 0.0   # 满减金额
    min_amount:    float = 0.0   # 门槛
    status:        str = 'draft'
    id:            Optional[int] = None
    created_at:    Optional[str] = None

    def to_dict(self) -> dict:
        return {'id': self.id, 'tenant_id': self.tenant_id, 'name': self.name,
                'promo_type': self.promo_type, 'discount_rate': self.discount_rate,
                'reduce_amount': self.reduce_amount, 'min_amount': self.min_amount,
                'start_at': self.start_at, 'end_at': self.end_at, 'status': self.status}

    @staticmethod
    def from_row(row) -> 'Promotion':
        r = tuple(row)
        p = Promotion(id=r[0], tenant_id=r[1], name=r[2], promo_type=r[3],
                      discount_rate=r[4], reduce_amount=r[5], min_amount=r[6],
                      start_at=r[7], end_at=r[8], status=r[9])
        p.created_at = r[10]
        return p


@dataclass
class Coupon:
    tenant_id:      int
    code:           str
    face_value:     float
    start_at:       str
    end_at:         str
    min_amount:     float = 0.0
    total_qty:      int = 1
    used_qty:       int = 0
    per_user_limit: int = 1
    status:         str = 'active'
    promotion_id:   Optional[int] = None
    id:             Optional[int] = None

    @property
    def remaining_qty(self) -> int:
        return self.total_qty - self.used_qty

    @staticmethod
    def from_row(row) -> 'Coupon':
        r = tuple(row)
        return Coupon(
            id=r[0], tenant_id=r[1], promotion_id=r[2], code=r[3],
            face_value=r[4], min_amount=r[5], total_qty=r[6],
            used_qty=r[7], per_user_limit=r[8], start_at=r[9],
            end_at=r[10], status=r[11],
        )


@dataclass
class CouponRecord:
    coupon_id:   int
    customer_id: int
    order_id:    Optional[int] = None
    used_at:     Optional[str] = None
    id:          Optional[int] = None
    created_at:  Optional[str] = None

    @staticmethod
    def from_row(row) -> 'CouponRecord':
        r = tuple(row)
        rec = CouponRecord(id=r[0], coupon_id=r[1], customer_id=r[2],
                           order_id=r[3], used_at=r[4])
        rec.created_at = r[5]
        return rec
