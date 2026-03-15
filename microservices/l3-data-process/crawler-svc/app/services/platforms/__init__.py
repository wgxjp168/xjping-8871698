"""Platform adapter registry."""
from __future__ import annotations

from typing import Dict

from app.models.schemas import Platform
from app.services.platforms.base import BasePlatformAdapter
from app.services.platforms.taobao import TaobaoAdapter
from app.services.platforms.jd import JDAdapter
from app.services.platforms.ali1688 import Ali1688Adapter
from app.services.platforms.pinduoduo import PinduoduoAdapter
from app.services.platforms.vipshop import VipshopAdapter
from app.services.platforms.suning import SuningAdapter
from app.services.platforms.douyin import DouyinAdapter

_REGISTRY: Dict[Platform, BasePlatformAdapter] = {
    Platform.TAOBAO:  TaobaoAdapter(),
    Platform.JD:      JDAdapter(),
    Platform.ALI1688: Ali1688Adapter(),
    Platform.PDD:     PinduoduoAdapter(),
    Platform.VIPSHOP: VipshopAdapter(),
    Platform.SUNING:  SuningAdapter(),
    Platform.DOUYIN:  DouyinAdapter(),
}


def get_adapter(platform: Platform) -> BasePlatformAdapter:
    adapter = _REGISTRY.get(platform)
    if adapter is None:
        raise ValueError(f"No adapter registered for platform: {platform}")
    return adapter


def all_adapters() -> Dict[Platform, BasePlatformAdapter]:
    return dict(_REGISTRY)
