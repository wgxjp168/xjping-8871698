from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Customer:
    tenant_id:  int
    name:       str = ''
    phone:      str = ''
    email:      str = ''
    user_id:    Optional[int] = None
    id:         Optional[int] = None
    created_at: Optional[str] = None

    @staticmethod
    def from_row(row) -> 'Customer':
        r = tuple(row)
        c = Customer(id=r[0], tenant_id=r[1], user_id=r[2],
                     name=r[3] or '', phone=r[4] or '', email=r[5] or '')
        c.created_at = r[6]
        return c


@dataclass
class OrderItem:
    order_id:     int
    product_id:   int
    product_name: str
    quantity:     int
    unit_price:   float
    subtotal:     float
    id:           Optional[int] = None

    @staticmethod
    def from_row(row) -> 'OrderItem':
        r = tuple(row)
        return OrderItem(id=r[0], order_id=r[1], product_id=r[2],
                         product_name=r[3], quantity=r[4],
                         unit_price=r[5], subtotal=r[6])


@dataclass
class Order:
    tenant_id:       int
    order_no:        str
    total_amount:    float
    pay_amount:      float
    customer_id:     Optional[int] = None
    mall_id:         Optional[int] = None
    discount_amount: float = 0.0
    status:          str = 'pending'
    remark:          str = ''
    id:              Optional[int] = None
    created_at:      Optional[str] = None
    updated_at:      Optional[str] = None
    items:           List[OrderItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {'id': self.id, 'order_no': self.order_no,
                'tenant_id': self.tenant_id, 'customer_id': self.customer_id,
                'total_amount': self.total_amount, 'pay_amount': self.pay_amount,
                'discount_amount': self.discount_amount, 'status': self.status,
                'items': [{'product_name': i.product_name, 'quantity': i.quantity,
                           'unit_price': i.unit_price} for i in self.items]}

    @staticmethod
    def from_row(row) -> 'Order':
        r = tuple(row)
        o = Order(id=r[0], tenant_id=r[1], mall_id=r[2], customer_id=r[3],
                  order_no=r[4], total_amount=r[5], discount_amount=r[6],
                  pay_amount=r[7], status=r[8], remark=r[9] or '')
        o.created_at = r[10]; o.updated_at = r[11]
        return o


@dataclass
class Payment:
    order_id:   int
    payment_no: str
    amount:     float
    method:     str = 'cash'
    status:     str = 'pending'
    paid_at:    Optional[str] = None
    id:         Optional[int] = None
    created_at: Optional[str] = None

    @staticmethod
    def from_row(row) -> 'Payment':
        r = tuple(row)
        p = Payment(id=r[0], order_id=r[1], payment_no=r[2],
                    amount=r[3], method=r[4], status=r[5], paid_at=r[6])
        p.created_at = r[7]
        return p
