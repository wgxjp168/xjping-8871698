"""模块 2：商场基础信息"""
from .models import Mall, Floor, Shop
from .mall_repository import MallRepository
from .shop_repository import ShopRepository

__all__ = ['Mall', 'Floor', 'Shop', 'MallRepository', 'ShopRepository']
