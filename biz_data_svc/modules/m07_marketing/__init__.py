"""模块 7：营销与促销"""
from .models import Promotion, Coupon, CouponRecord
from .promotion_repository import PromotionRepository
from .coupon_repository import CouponRepository

__all__ = [
    'Promotion', 'Coupon', 'CouponRecord',
    'PromotionRepository', 'CouponRepository',
]
