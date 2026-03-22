"""
C端商城模块 — 领域模型
涉及表：categories, products, product_skus, product_inventory,
        product_images, cart_items, delivery_addresses
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


# --------------------------------------------------------------------------- #
#  1. Category（商品分类）                                                       #
# --------------------------------------------------------------------------- #

@dataclass
class Category:
    tenant_id: int
    name: str
    id: Optional[int] = None
    parent_id: Optional[int] = None
    icon_url: Optional[str] = None
    banner_url: Optional[str] = None
    sort_order: int = 0
    level: int = 1
    path: str = ''             # 例如 "0/1/5"
    status: str = 'active'    # 'active' | 'inactive'
    created_at: Optional[str] = None

    # from_row 列顺序：id,tenant_id,name,parent_id,icon_url,banner_url,
    #                  sort_order,level,path,status,created_at
    @classmethod
    def from_row(cls, row: tuple) -> 'Category':
        return cls(
            id=row[0],
            tenant_id=row[1],
            name=row[2],
            parent_id=row[3],
            icon_url=row[4],
            banner_url=row[5],
            sort_order=row[6],
            level=row[7],
            path=row[8],
            status=row[9],
            created_at=row[10],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'parent_id': self.parent_id,
            'icon_url': self.icon_url,
            'banner_url': self.banner_url,
            'sort_order': self.sort_order,
            'level': self.level,
            'path': self.path,
            'status': self.status,
            'created_at': self.created_at,
        }


# --------------------------------------------------------------------------- #
#  2. Product（商品）                                                            #
# --------------------------------------------------------------------------- #

@dataclass
class Product:
    tenant_id: int
    category_id: int
    name: str
    id: Optional[int] = None
    supplier_id: Optional[int] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    unit: Optional[str] = None
    weight: Optional[float] = None
    status: str = 'draft'      # 'draft' | 'on_sale' | 'off_sale'
    is_featured: int = 0
    tags: Optional[str] = None
    sales_count: int = 0
    view_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # from_row 列顺序：id,tenant_id,category_id,supplier_id,name,subtitle,
    #                  description,cover_image,unit,weight,status,is_featured,
    #                  tags,sales_count,view_count,created_at,updated_at
    @classmethod
    def from_row(cls, row: tuple) -> 'Product':
        return cls(
            id=row[0],
            tenant_id=row[1],
            category_id=row[2],
            supplier_id=row[3],
            name=row[4],
            subtitle=row[5],
            description=row[6],
            cover_image=row[7],
            unit=row[8],
            weight=row[9],
            status=row[10],
            is_featured=int(row[11] or 0),
            tags=row[12],
            sales_count=row[13] or 0,
            view_count=row[14] or 0,
            created_at=row[15],
            updated_at=row[16],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'category_id': self.category_id,
            'supplier_id': self.supplier_id,
            'name': self.name,
            'subtitle': self.subtitle,
            'description': self.description,
            'cover_image': self.cover_image,
            'unit': self.unit,
            'weight': self.weight,
            'status': self.status,
            'is_featured': self.is_featured,
            'tags': self.tags,
            'sales_count': self.sales_count,
            'view_count': self.view_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Product':
        """从字典（Redis 缓存反序列化）恢复 Product 对象。"""
        return cls(
            id=d.get('id'),
            tenant_id=d['tenant_id'],
            category_id=d['category_id'],
            supplier_id=d.get('supplier_id'),
            name=d['name'],
            subtitle=d.get('subtitle'),
            description=d.get('description'),
            cover_image=d.get('cover_image'),
            unit=d.get('unit'),
            weight=d.get('weight'),
            status=d.get('status', 'draft'),
            is_featured=int(d.get('is_featured', 0)),
            tags=d.get('tags'),
            sales_count=int(d.get('sales_count', 0)),
            view_count=int(d.get('view_count', 0)),
            created_at=d.get('created_at'),
            updated_at=d.get('updated_at'),
        )


# --------------------------------------------------------------------------- #
#  3. ProductSku（商品规格/SKU）                                                 #
# --------------------------------------------------------------------------- #

@dataclass
class ProductSku:
    product_id: int
    sku_code: str
    cost_price: float
    market_price: float
    sale_price: float
    id: Optional[int] = None
    barcode: Optional[str] = None
    attributes: Optional[str] = None   # JSON 字符串
    status: str = 'active'             # 'active' | 'inactive'
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # from_row 列顺序：id,product_id,sku_code,barcode,attributes,
    #                  cost_price,market_price,sale_price,status,created_at,updated_at
    @classmethod
    def from_row(cls, row: tuple) -> 'ProductSku':
        return cls(
            id=row[0],
            product_id=row[1],
            sku_code=row[2],
            barcode=row[3],
            attributes=row[4],
            cost_price=row[5],
            market_price=row[6],
            sale_price=row[7],
            status=row[8],
            created_at=row[9],
            updated_at=row[10],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'product_id': self.product_id,
            'sku_code': self.sku_code,
            'barcode': self.barcode,
            'attributes': self.attributes,
            'cost_price': self.cost_price,
            'market_price': self.market_price,
            'sale_price': self.sale_price,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


# --------------------------------------------------------------------------- #
#  4. ProductInventory（库存）                                                   #
# --------------------------------------------------------------------------- #

@dataclass
class ProductInventory:
    sku_id: int
    warehouse_id: int
    quantity: int
    id: Optional[int] = None
    reserved: int = 0
    safety_stock: int = 0
    updated_at: Optional[str] = None

    # from_row 列顺序：id,sku_id,warehouse_id,quantity,reserved,safety_stock,updated_at
    @classmethod
    def from_row(cls, row: tuple) -> 'ProductInventory':
        return cls(
            id=row[0],
            sku_id=row[1],
            warehouse_id=row[2],
            quantity=row[3],
            reserved=row[4],
            safety_stock=row[5],
            updated_at=row[6],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'sku_id': self.sku_id,
            'warehouse_id': self.warehouse_id,
            'quantity': self.quantity,
            'reserved': self.reserved,
            'safety_stock': self.safety_stock,
            'updated_at': self.updated_at,
        }


# --------------------------------------------------------------------------- #
#  5. ProductImage（商品图片）                                                   #
# --------------------------------------------------------------------------- #

@dataclass
class ProductImage:
    product_id: int
    url: str
    id: Optional[int] = None
    sku_id: Optional[int] = None
    sort_order: int = 0
    is_cover: int = 0

    # from_row 列顺序：id,product_id,sku_id,url,sort_order,is_cover
    @classmethod
    def from_row(cls, row: tuple) -> 'ProductImage':
        return cls(
            id=row[0],
            product_id=row[1],
            sku_id=row[2],
            url=row[3],
            sort_order=row[4],
            is_cover=int(row[5] or 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'product_id': self.product_id,
            'sku_id': self.sku_id,
            'url': self.url,
            'sort_order': self.sort_order,
            'is_cover': self.is_cover,
        }


# --------------------------------------------------------------------------- #
#  6. CartItem（购物车条目）                                                     #
# --------------------------------------------------------------------------- #

@dataclass
class CartItem:
    user_id: int
    tenant_id: int
    product_id: int
    sku_id: int
    quantity: int
    id: Optional[int] = None
    is_selected: int = 1
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # from_row 列顺序：id,user_id,tenant_id,product_id,sku_id,
    #                  quantity,is_selected,created_at,updated_at
    @classmethod
    def from_row(cls, row: tuple) -> 'CartItem':
        return cls(
            id=row[0],
            user_id=row[1],
            tenant_id=row[2],
            product_id=row[3],
            sku_id=row[4],
            quantity=row[5],
            is_selected=int(row[6] or 0),
            created_at=row[7],
            updated_at=row[8],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'product_id': self.product_id,
            'sku_id': self.sku_id,
            'quantity': self.quantity,
            'is_selected': self.is_selected,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


# --------------------------------------------------------------------------- #
#  7. DeliveryAddress（收货地址）                                                #
# --------------------------------------------------------------------------- #

@dataclass
class DeliveryAddress:
    user_id: int
    receiver_name: str
    phone: str
    province: str
    city: str
    district: str
    address_detail: str
    id: Optional[int] = None
    street: Optional[str] = None
    postal_code: Optional[str] = None
    is_default: int = 0
    tag: Optional[str] = None       # 例如 '家' | '公司'
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # from_row 列顺序：id,user_id,receiver_name,phone,province,city,district,
    #                  street,address_detail,postal_code,is_default,tag,
    #                  created_at,updated_at
    @classmethod
    def from_row(cls, row: tuple) -> 'DeliveryAddress':
        return cls(
            id=row[0],
            user_id=row[1],
            receiver_name=row[2],
            phone=row[3],
            province=row[4],
            city=row[5],
            district=row[6],
            street=row[7],
            address_detail=row[8],
            postal_code=row[9],
            is_default=int(row[10] or 0),
            tag=row[11],
            created_at=row[12],
            updated_at=row[13],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'receiver_name': self.receiver_name,
            'phone': self.phone,
            'province': self.province,
            'city': self.city,
            'district': self.district,
            'street': self.street,
            'address_detail': self.address_detail,
            'postal_code': self.postal_code,
            'is_default': self.is_default,
            'tag': self.tag,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
