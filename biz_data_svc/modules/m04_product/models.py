from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    tenant_id:  int
    name:       str
    parent_id:  Optional[int] = None
    sort_order: int = 0
    id:         Optional[int] = None

    def to_dict(self) -> dict:
        return {'id': self.id, 'tenant_id': self.tenant_id, 'name': self.name,
                'parent_id': self.parent_id, 'sort_order': self.sort_order}

    @staticmethod
    def from_row(row) -> 'Category':
        r = tuple(row)
        return Category(id=r[0], tenant_id=r[1], name=r[2],
                        parent_id=r[3], sort_order=r[4] or 0)


@dataclass
class Brand:
    tenant_id: int
    name:      str
    logo_url:  str = ''
    id:        Optional[int] = None

    @staticmethod
    def from_row(row) -> 'Brand':
        r = tuple(row)
        return Brand(id=r[0], tenant_id=r[1], name=r[2], logo_url=r[3] or '')


@dataclass
class Product:
    tenant_id:   int
    category_id: int
    name:        str
    sku:         str
    cost_price:  float
    sale_price:  float
    brand_id:    Optional[int] = None
    barcode:     str = ''
    unit:        str = '件'
    description: str = ''
    image_url:   str = ''
    status:      str = 'on_sale'
    id:          Optional[int] = None
    created_at:  Optional[str] = None
    updated_at:  Optional[str] = None

    def to_dict(self) -> dict:
        return {'id': self.id, 'tenant_id': self.tenant_id,
                'category_id': self.category_id, 'brand_id': self.brand_id,
                'name': self.name, 'sku': self.sku, 'barcode': self.barcode,
                'cost_price': self.cost_price, 'sale_price': self.sale_price,
                'status': self.status}

    @staticmethod
    def from_row(row) -> 'Product':
        r = tuple(row)
        p = Product(
            id=r[0], tenant_id=r[1], category_id=r[2], brand_id=r[3],
            name=r[4], sku=r[5], barcode=r[6] or '', unit=r[7] or '件',
            cost_price=r[8], sale_price=r[9], description=r[10] or '',
            image_url=r[11] or '', status=r[12],
        )
        p.created_at = r[13]; p.updated_at = r[14]
        return p
