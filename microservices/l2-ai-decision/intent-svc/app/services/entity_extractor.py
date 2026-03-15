"""
Entity Extractor Service for ILbuy Intent Service.

Extracts structured product/shopping entities from Chinese e-commerce text
using a combination of:
1. Curated brand/category dictionaries (exact + partial match)
2. Regex patterns for budget, specs, quantity, delivery_time, and model numbers
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from app.models.schemas import (
    EntityExtractRequest,
    EntityExtractResponse,
    ExtractedEntities,
    RawEntity,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand list  (ordered: longer / more specific names first to avoid shadowing)
# ---------------------------------------------------------------------------

BRAND_LIST: list[str] = [
    # Chinese brands
    "小米", "红米", "华为", "荣耀", "苹果", "三星", "海尔",
    "格力", "美的", "联想", "戴尔", "索尼", "LG", "飞利浦",
    "松下", "西门子", "博世", "大疆", "OPPO", "vivo", "一加",
    "魅族", "中兴", "努比亚", "TCL", "创维", "海信", "长虹",
    "康佳", "奥克斯", "志高", "科龙", "华凌", "统帅",
    "容声", "澳柯玛", "万和", "万家乐",
    # Laptops / PCs
    "宏碁", "华硕", "惠普", "HP", "微软", "雷蛇",
    # Audio / accessories
    "森海塞尔", "漫步者", "哈曼", "JBL",
    # Normalised ASCII variants kept for matching
    "Apple", "Samsung", "Huawei", "Xiaomi",
]

# Sorted longest-first to prevent partial matches swallowing longer brand names
BRAND_LIST_SORTED: list[str] = sorted(BRAND_LIST, key=len, reverse=True)

# ---------------------------------------------------------------------------
# Category list
# ---------------------------------------------------------------------------

CATEGORY_LIST: list[str] = [
    "手机", "电脑", "笔记本", "平板", "电视", "冰箱", "空调",
    "洗衣机", "微波炉", "热水器", "油烟机", "净水器", "吸尘器",
    "扫地机器人", "投影仪", "耳机", "音箱", "路由器", "相机",
    "摄像机", "游戏机", "智能手表", "可穿戴", "打印机",
    "显示器", "键盘", "鼠标",
]

CATEGORY_LIST_SORTED: list[str] = sorted(CATEGORY_LIST, key=len, reverse=True)

# ---------------------------------------------------------------------------
# Spec patterns  (key → regex pattern)
# ---------------------------------------------------------------------------

SPECS_PATTERNS: dict[str, re.Pattern] = {
    "ram": re.compile(
        r"(\d+)\s*[Gg][Bb]?\s*(?:\+|内存|RAM|ram)?", re.IGNORECASE
    ),
    "storage": re.compile(
        r"(\d+)\s*[Gg][Bb]?\s*(?:存储|硬盘|闪存|SSD|ROM|rom)?", re.IGNORECASE
    ),
    "ram_storage_combo": re.compile(
        r"(\d+)\s*[Gg]?\s*\+\s*(\d+)\s*[Gg]", re.IGNORECASE
    ),
    "screen_size": re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:英寸|寸|inch)", re.IGNORECASE
    ),
    "battery": re.compile(
        r"(\d+)\s*(?:[mM][aA][hH]|毫安)", re.IGNORECASE
    ),
    "cpu": re.compile(
        r"(?:骁龙|天玑|麒麟|苹果A|Exynos|i[3579]|Ryzen|Core)\s*[\w\d]+",
        re.IGNORECASE,
    ),
    "color": re.compile(
        r"(?:颜色|色)?(?:黑色|白色|蓝色|绿色|金色|银色|红色|紫色|粉色|灰色|深空黑|曜石黑|星光色)",
    ),
    "resolution": re.compile(
        r"(\d{3,4})\s*[xX×]\s*(\d{3,4})", re.IGNORECASE
    ),
}

# ---------------------------------------------------------------------------
# Budget patterns
# ---------------------------------------------------------------------------

# Patterns that capture a numeric value and an optional unit (万/千)
BUDGET_PATTERN_EXACT = re.compile(
    r"(?P<budget_label>预算|价格|花费|售价|多少钱)?\s*"
    r"(?P<num>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>[万千百]?)\s*"
    r"(?P<currency>元|[¥￥])?",
    re.UNICODE,
)

BUDGET_MAX_PATTERN = re.compile(
    r"(?:预算|不超过|控制在|最多|最高|上限)\s*"
    r"(?P<num>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>[万千百]?)\s*"
    r"(?P<currency>元|[¥￥])?",
    re.UNICODE,
)

BUDGET_MIN_PATTERN = re.compile(
    r"(?:至少|最少|不低于|最低|下限)\s*"
    r"(?P<num>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>[万千百]?)\s*"
    r"(?P<currency>元|[¥￥])?",
    re.UNICODE,
)

BUDGET_RANGE_PATTERN = re.compile(
    r"(?P<min_num>\d+(?:\.\d+)?)\s*(?P<min_unit>[万千百]?)\s*(?:元|[¥￥])?\s*"
    r"(?:到|至|-|—|~)\s*"
    r"(?P<max_num>\d+(?:\.\d+)?)\s*(?P<max_unit>[万千百]?)\s*(?:元|[¥￥])?",
    re.UNICODE,
)

# ---------------------------------------------------------------------------
# Quantity patterns
# ---------------------------------------------------------------------------

QUANTITY_PATTERN = re.compile(
    r"(?P<num>\d+)\s*(?:台|部|个|件|套|箱|批|条|只|架|块)",
    re.UNICODE,
)

# ---------------------------------------------------------------------------
# Delivery time patterns
# ---------------------------------------------------------------------------

DELIVERY_PATTERNS: list[re.Pattern] = [
    re.compile(r"(明天|后天|今天|当天)", re.UNICODE),
    re.compile(r"(\d+)\s*天\s*[内以]", re.UNICODE),
    re.compile(r"(本周|下周|这周|下个月|本月)\s*[内]?", re.UNICODE),
    re.compile(r"(尽快|越快越好|加急|急需|急)", re.UNICODE),
    re.compile(r"(\d{1,2})[/\-月]\s*(\d{1,2})[日号]?\s*前", re.UNICODE),
]

# ---------------------------------------------------------------------------
# Model number patterns
# ---------------------------------------------------------------------------

MODEL_PATTERNS: list[re.Pattern] = [
    # e.g. Mate60 Pro, iPhone 15 Pro Max, 13 Pro, Mate X5
    re.compile(
        r"\b(?:Pro\s*Max|Ultra|Plus|Max|Pro|Lite|SE|Neo|Note|Fold|Flip|Air|Mini)?\s*"
        r"[A-Z][\w\d]+\s*"
        r"(?:Pro\s*Max|Ultra|Plus|Max|Pro|Lite|SE|Neo|Note|Fold|Flip|Air|Mini)?\b",
        re.UNICODE,
    ),
    # e.g. 小米13 / 华为P60
    re.compile(
        r"(?<=[\u4e00-\u9fff])\d+\s*"
        r"(?:Pro\s*Max|Ultra|Plus|Max|Pro|Lite|SE|Neo|Fold|Flip|Air|Mini)?",
        re.UNICODE,
    ),
    # e.g. MX550, RTX 4080, i9-14900
    re.compile(
        r"\b[A-Z]{1,5}\s*-?\d{3,6}[A-Z0-9]?\b",
        re.UNICODE,
    ),
]


def _unit_multiplier(unit: str) -> float:
    """Convert Chinese unit suffix to numeric multiplier."""
    mapping = {"万": 10_000, "千": 1_000, "百": 100, "": 1}
    return float(mapping.get(unit, 1))


class EntityExtractor:
    """
    Rule-based entity extractor for Chinese e-commerce text.

    All extraction is deterministic — no model weights required.
    """

    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        """Pre-compile patterns. Idempotent."""
        logger.info("EntityExtractor initialised (rule-based, no model weights).")
        self._initialized = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        text: str,
        intent: Optional[str] = None,
    ) -> EntityExtractResponse:
        """
        Extract structured entities from Chinese shopping text.

        Parameters
        ----------
        text:   Raw user utterance.
        intent: Optional primary intent (may tune extraction heuristics).

        Returns
        -------
        EntityExtractResponse with structured entities and raw spans.
        """
        raw_entities: list[RawEntity] = []

        brand = self._extract_brand(text, raw_entities)
        category = self._extract_category(text, raw_entities)
        model = self._extract_model(text, brand, raw_entities)
        budget_min, budget_max = self._extract_budget(text, raw_entities)
        specs = self._extract_specs(text, raw_entities)
        quantity = self._extract_quantity(text, raw_entities)
        delivery_time = self._extract_delivery_time(text, raw_entities)

        entities = ExtractedEntities(
            brand=brand,
            model=model,
            budget_min=budget_min,
            budget_max=budget_max,
            category=category,
            specs=specs if specs else None,
            quantity=quantity,
            delivery_time=delivery_time,
        )

        return EntityExtractResponse(
            entities=entities,
            raw_entities=raw_entities,
        )

    # ------------------------------------------------------------------
    # Private extraction helpers
    # ------------------------------------------------------------------

    def _extract_brand(self, text: str, raw_entities: list[RawEntity]) -> Optional[str]:
        for brand in BRAND_LIST_SORTED:
            idx = text.find(brand)
            if idx != -1:
                raw_entities.append(
                    RawEntity(
                        entity_type="brand",
                        value=brand,
                        start=idx,
                        end=idx + len(brand),
                        confidence=0.95,
                    )
                )
                return brand
        return None

    def _extract_category(self, text: str, raw_entities: list[RawEntity]) -> Optional[str]:
        for category in CATEGORY_LIST_SORTED:
            idx = text.find(category)
            if idx != -1:
                raw_entities.append(
                    RawEntity(
                        entity_type="category",
                        value=category,
                        start=idx,
                        end=idx + len(category),
                        confidence=0.92,
                    )
                )
                return category
        return None

    def _extract_model(
        self,
        text: str,
        brand: Optional[str],
        raw_entities: list[RawEntity],
    ) -> Optional[str]:
        """Try to extract a product model string."""
        for pattern in MODEL_PATTERNS:
            match = pattern.search(text)
            if match:
                value = match.group(0).strip()
                # Avoid returning the brand name itself as a model
                if brand and value == brand:
                    continue
                # Minimum length guard
                if len(value) < 2:
                    continue
                raw_entities.append(
                    RawEntity(
                        entity_type="model",
                        value=value,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.80,
                    )
                )
                return value
        return None

    def _extract_budget(
        self,
        text: str,
        raw_entities: list[RawEntity],
    ) -> tuple[Optional[float], Optional[float]]:
        """Extract budget_min and budget_max from text."""
        budget_min: Optional[float] = None
        budget_max: Optional[float] = None

        # Check for explicit range first: "3000元到5000元"
        range_match = BUDGET_RANGE_PATTERN.search(text)
        if range_match:
            min_val = float(range_match.group("min_num")) * _unit_multiplier(
                range_match.group("min_unit") or ""
            )
            max_val = float(range_match.group("max_num")) * _unit_multiplier(
                range_match.group("max_unit") or ""
            )
            budget_min = min_val
            budget_max = max_val
            raw_entities.append(
                RawEntity(
                    entity_type="budget_range",
                    value=range_match.group(0),
                    start=range_match.start(),
                    end=range_match.end(),
                    confidence=0.90,
                )
            )
            return budget_min, budget_max

        # Check explicit max: "预算5000以内"
        max_match = BUDGET_MAX_PATTERN.search(text)
        if max_match:
            budget_max = float(max_match.group("num")) * _unit_multiplier(
                max_match.group("unit") or ""
            )
            raw_entities.append(
                RawEntity(
                    entity_type="budget_max",
                    value=max_match.group(0),
                    start=max_match.start(),
                    end=max_match.end(),
                    confidence=0.88,
                )
            )

        # Check explicit min: "至少3000元"
        min_match = BUDGET_MIN_PATTERN.search(text)
        if min_match:
            budget_min = float(min_match.group("num")) * _unit_multiplier(
                min_match.group("unit") or ""
            )
            raw_entities.append(
                RawEntity(
                    entity_type="budget_min",
                    value=min_match.group(0),
                    start=min_match.start(),
                    end=min_match.end(),
                    confidence=0.88,
                )
            )

        # If still no budget found, try generic number + 元 pattern
        if budget_min is None and budget_max is None:
            for m in BUDGET_PATTERN_EXACT.finditer(text):
                num = m.group("num")
                unit = m.group("unit") or ""
                currency = m.group("currency")
                if num and (currency or unit):
                    val = float(num) * _unit_multiplier(unit)
                    if val > 0:
                        budget_max = val
                        raw_entities.append(
                            RawEntity(
                                entity_type="budget_approx",
                                value=m.group(0),
                                start=m.start(),
                                end=m.end(),
                                confidence=0.70,
                            )
                        )
                        break

        return budget_min, budget_max

    def _extract_specs(
        self,
        text: str,
        raw_entities: list[RawEntity],
    ) -> dict[str, Any]:
        """Extract product specification key-value pairs."""
        specs: dict[str, Any] = {}

        # RAM+Storage combo: "8+256"  or "8G+256G"
        combo_match = SPECS_PATTERNS["ram_storage_combo"].search(text)
        if combo_match:
            specs["ram"] = combo_match.group(1) + "GB"
            specs["storage"] = combo_match.group(2) + "GB"
            raw_entities.append(
                RawEntity(
                    entity_type="specs_combo",
                    value=combo_match.group(0),
                    start=combo_match.start(),
                    end=combo_match.end(),
                    confidence=0.93,
                )
            )
        else:
            # Individual RAM / storage
            for key in ("ram", "storage"):
                m = SPECS_PATTERNS[key].search(text)
                if m and m.group(1):
                    val = int(m.group(1))
                    if val in (2, 3, 4, 6, 8, 12, 16, 24, 32, 64):  # plausible GB counts
                        specs[key] = f"{val}GB"

        for key in ("screen_size", "battery", "cpu", "color", "resolution"):
            m = SPECS_PATTERNS[key].search(text)
            if m:
                specs[key] = m.group(0).strip()
                raw_entities.append(
                    RawEntity(
                        entity_type=f"specs_{key}",
                        value=m.group(0),
                        start=m.start(),
                        end=m.end(),
                        confidence=0.85,
                    )
                )

        return specs

    def _extract_quantity(
        self,
        text: str,
        raw_entities: list[RawEntity],
    ) -> Optional[int]:
        m = QUANTITY_PATTERN.search(text)
        if m:
            raw_entities.append(
                RawEntity(
                    entity_type="quantity",
                    value=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    confidence=0.90,
                )
            )
            return int(m.group("num"))
        return None

    def _extract_delivery_time(
        self,
        text: str,
        raw_entities: list[RawEntity],
    ) -> Optional[str]:
        for pattern in DELIVERY_PATTERNS:
            m = pattern.search(text)
            if m:
                raw_entities.append(
                    RawEntity(
                        entity_type="delivery_time",
                        value=m.group(0),
                        start=m.start(),
                        end=m.end(),
                        confidence=0.85,
                    )
                )
                return m.group(0)
        return None
