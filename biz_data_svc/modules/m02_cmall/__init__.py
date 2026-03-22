"""
C端商城模块（m02_cmall）
涉及表：categories, products, product_skus, product_inventory,
        product_images, cart_items, delivery_addresses
"""

# 领域模型
from .models import (
    Category,
    Product,
    ProductSku,
    ProductInventory,
    ProductImage,
    CartItem,
    DeliveryAddress,
)

# 数据访问层
from .category_repository import CategoryRepository
from .product_repository import ProductRepository
from .sku_repository import SkuRepository
from .inventory_repository import InventoryRepository
from .cart_repository import CartRepository
from .address_repository import AddressRepository

__all__ = [
    # Models
    'Category',
    'Product',
    'ProductSku',
    'ProductInventory',
    'ProductImage',
    'CartItem',
    'DeliveryAddress',
    # Repositories
    'CategoryRepository',
    'ProductRepository',
    'SkuRepository',
    'InventoryRepository',
    'CartRepository',
    'AddressRepository',
]
