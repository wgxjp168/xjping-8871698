from dataclasses import dataclass
from typing import Optional


@dataclass
class Mall:
    tenant_id:  int
    name:       str
    address:    str = ''
    city:       str = ''
    province:   str = ''
    phone:      str = ''
    status:     str = 'open'
    id:         Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {'id': self.id, 'tenant_id': self.tenant_id, 'name': self.name,
                'address': self.address, 'city': self.city,
                'province': self.province, 'status': self.status}

    @staticmethod
    def from_row(row) -> 'Mall':
        r = tuple(row)
        m = Mall(id=r[0], tenant_id=r[1], name=r[2], address=r[3] or '',
                 city=r[4] or '', province=r[5] or '', phone=r[6] or '', status=r[7])
        m.created_at = r[8]; m.updated_at = r[9]
        return m


@dataclass
class Floor:
    mall_id:     int
    floor_no:    str
    description: str = ''
    id:          Optional[int] = None

    @staticmethod
    def from_row(row) -> 'Floor':
        r = tuple(row)
        return Floor(id=r[0], mall_id=r[1], floor_no=r[2], description=r[3] or '')


@dataclass
class Shop:
    mall_id:  int
    name:     str
    shop_no:  str
    floor_id: Optional[int] = None
    area:     float = 0.0
    status:   str = 'vacant'
    id:       Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {'id': self.id, 'mall_id': self.mall_id, 'name': self.name,
                'shop_no': self.shop_no, 'floor_id': self.floor_id,
                'area': self.area, 'status': self.status}

    @staticmethod
    def from_row(row) -> 'Shop':
        r = tuple(row)
        s = Shop(id=r[0], mall_id=r[1], floor_id=r[2], name=r[3],
                 shop_no=r[4], area=r[5] or 0.0, status=r[6])
        s.created_at = r[7]; s.updated_at = r[8]
        return s
