"""
Drools-inspired Python rule engine for purchase-decision evaluation.

Rules are registered with a priority (lower number = higher priority) and
executed in that order.  All rules are evaluated; results are aggregated into
a RuleResult.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

from app.models.schemas import RuleResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule dataclass
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    """A single evaluatable business rule."""
    id: str
    name: str
    priority: int  # lower = higher priority
    condition: Callable[[dict], bool]   # returns True when rule *should fire*
    action: Callable[[dict], tuple[str, str]]  # returns (severity, message)
    category: str  # budget | brand | compliance | risk | logistics


# ---------------------------------------------------------------------------
# Built-in rule implementations
# ---------------------------------------------------------------------------

def _rule_001_condition(ctx: dict) -> bool:
    """Fire when budget is specified and product_price exceeds it."""
    budget = ctx.get("budget")
    price = ctx.get("product_price")
    return budget is not None and price is not None and price > budget


def _rule_001_action(ctx: dict) -> tuple[str, str]:
    budget = ctx.get("budget", 0)
    price = ctx.get("product_price", 0)
    return (
        "violation",
        f"产品价格 ¥{price:.2f} 超出预算 ¥{budget:.2f}"
        f"（超出 {((price - budget) / budget * 100):.1f}%）",
    )


def _rule_002_condition(ctx: dict) -> bool:
    """Fire for B2B orders where quantity is below the Minimum Order Quantity."""
    is_b2b = ctx.get("is_b2b", False)
    quantity = ctx.get("order_quantity")
    moq = ctx.get("min_order_quantity")
    return is_b2b and quantity is not None and moq is not None and quantity < moq


def _rule_002_action(ctx: dict) -> tuple[str, str]:
    qty = ctx.get("order_quantity", 0)
    moq = ctx.get("min_order_quantity", 0)
    return (
        "violation",
        f"订单数量 {qty} 低于最小起订量 {moq}，需要追加 {moq - qty} 件",
    )


def _rule_003_condition(ctx: dict) -> bool:
    """Fire for B2B orders where the brand is not in the approved list."""
    is_b2b = ctx.get("is_b2b", False)
    brand = ctx.get("brand", "")
    approved = ctx.get("approved_brands", [])
    return is_b2b and bool(brand) and bool(approved) and brand not in approved


def _rule_003_action(ctx: dict) -> tuple[str, str]:
    brand = ctx.get("brand", "未知品牌")
    return (
        "warning",
        f"品牌 '{brand}' 不在企业采购白名单中，请合规部门审核",
    )


def _rule_004_condition(ctx: dict) -> bool:
    """Fire when delivery_time exceeds the buyer's max_allowed_days."""
    delivery_time = ctx.get("delivery_time_days")
    max_allowed = ctx.get("max_delivery_days")
    return (
        delivery_time is not None
        and max_allowed is not None
        and delivery_time > max_allowed
    )


def _rule_004_action(ctx: dict) -> tuple[str, str]:
    dt = ctx.get("delivery_time_days", 0)
    mx = ctx.get("max_delivery_days", 0)
    return (
        "warning",
        f"预计交货周期 {dt} 天超出要求的 {mx} 天，建议选择库存充足的供应商",
    )


def _rule_005_condition(ctx: dict) -> bool:
    """Fire when the product category is restricted."""
    category = ctx.get("product_category", "")
    restricted = ctx.get("restricted_categories", [])
    return bool(category) and category in restricted


def _rule_005_action(ctx: dict) -> tuple[str, str]:
    category = ctx.get("product_category", "")
    return (
        "violation",
        f"产品类别 '{category}' 属于受限类别，需要额外审批流程",
    )


def _rule_006_condition(ctx: dict) -> bool:
    """Fire when a similar order was placed within the last 24 hours."""
    last_order_time_str = ctx.get("last_similar_order_time")
    if not last_order_time_str:
        return False
    try:
        if isinstance(last_order_time_str, datetime):
            last_order_time = last_order_time_str
        else:
            last_order_time = datetime.fromisoformat(str(last_order_time_str))
        return datetime.utcnow() - last_order_time < timedelta(hours=24)
    except (ValueError, TypeError):
        return False


def _rule_006_action(ctx: dict) -> tuple[str, str]:
    return (
        "warning",
        "检测到24小时内存在相似订单，请确认是否为重复提交",
    )


def _rule_007_condition(ctx: dict) -> bool:
    """Fire when product price is more than 3× the market reference price."""
    price = ctx.get("product_price")
    market_price = ctx.get("market_reference_price")
    return price is not None and market_price is not None and price > 3 * market_price


def _rule_007_action(ctx: dict) -> tuple[str, str]:
    price = ctx.get("product_price", 0)
    market_price = ctx.get("market_reference_price", 0)
    ratio = price / market_price if market_price > 0 else 0
    return (
        "warning",
        f"产品定价 ¥{price:.2f} 是市场参考价 ¥{market_price:.2f} 的 {ratio:.1f}x，"
        "价格偏高，建议重新询价",
    )


def _rule_008_condition(ctx: dict) -> bool:
    """Fire when required specs are incompatible with product specs."""
    required_specs = ctx.get("required_specs", {})
    product_specs = ctx.get("product_specs", {})
    if not required_specs or not product_specs:
        return False
    for key, required_value in required_specs.items():
        product_value = product_specs.get(key)
        if product_value is None:
            continue
        # Numeric: required value must be satisfied by product value
        if isinstance(required_value, (int, float)) and isinstance(product_value, (int, float)):
            # If the required spec key hints at a minimum (e.g. memory, capacity)
            # we treat required_value as a floor
            if product_value < required_value * 0.9:  # 10% tolerance
                return True
        elif isinstance(required_value, str) and isinstance(product_value, str):
            if required_value.lower() != product_value.lower():
                return True
    return False


def _rule_008_action(ctx: dict) -> tuple[str, str]:
    required_specs = ctx.get("required_specs", {})
    product_specs = ctx.get("product_specs", {})
    mismatches = []
    for key, req_val in required_specs.items():
        prod_val = product_specs.get(key)
        if prod_val is not None:
            if isinstance(req_val, (int, float)) and isinstance(prod_val, (int, float)):
                if prod_val < req_val * 0.9:
                    mismatches.append(f"{key}: 需要≥{req_val}，实际{prod_val}")
            elif isinstance(req_val, str) and isinstance(prod_val, str):
                if req_val.lower() != prod_val.lower():
                    mismatches.append(f"{key}: 需要'{req_val}'，实际'{prod_val}'")
    details = "；".join(mismatches) if mismatches else "规格不兼容"
    return (
        "violation",
        f"产品规格与需求不兼容：{details}",
    )


# ---------------------------------------------------------------------------
# Pre-defined rule registry
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[Rule] = [
    Rule(
        id="RULE_001",
        name="budget_check",
        priority=10,
        condition=_rule_001_condition,
        action=_rule_001_action,
        category="budget",
    ),
    Rule(
        id="RULE_002",
        name="min_order_quantity",
        priority=20,
        condition=_rule_002_condition,
        action=_rule_002_action,
        category="logistics",
    ),
    Rule(
        id="RULE_003",
        name="brand_compliance",
        priority=30,
        condition=_rule_003_condition,
        action=_rule_003_action,
        category="compliance",
    ),
    Rule(
        id="RULE_004",
        name="delivery_feasibility",
        priority=40,
        condition=_rule_004_condition,
        action=_rule_004_action,
        category="logistics",
    ),
    Rule(
        id="RULE_005",
        name="category_restriction",
        priority=15,
        condition=_rule_005_condition,
        action=_rule_005_action,
        category="compliance",
    ),
    Rule(
        id="RULE_006",
        name="duplicate_order",
        priority=50,
        condition=_rule_006_condition,
        action=_rule_006_action,
        category="risk",
    ),
    Rule(
        id="RULE_007",
        name="price_reasonableness",
        priority=25,
        condition=_rule_007_condition,
        action=_rule_007_action,
        category="budget",
    ),
    Rule(
        id="RULE_008",
        name="spec_compatibility",
        priority=12,
        condition=_rule_008_condition,
        action=_rule_008_action,
        category="compliance",
    ),
]


# ---------------------------------------------------------------------------
# RuleEngine class
# ---------------------------------------------------------------------------

class RuleEngine:
    """
    Drools-inspired rule engine.

    Rules are evaluated in ascending priority order. All rules are evaluated
    (no short-circuit) so that the full set of violations and warnings is
    reported in a single pass.
    """

    def __init__(self) -> None:
        self.rules: list[Rule] = []
        for rule in DEFAULT_RULES:
            self.register_rule(rule)

    def register_rule(self, rule: Rule) -> None:
        """Register a rule and maintain sorted order by priority."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)
        logger.debug("Registered rule %s (priority=%d)", rule.id, rule.priority)

    def evaluate(self, context: dict[str, Any]) -> RuleResult:
        """
        Evaluate all registered rules against the provided context dictionary.

        Returns a RuleResult with violations, warnings, and applied_rules lists.
        """
        violations: list[str] = []
        warnings: list[str] = []
        applied_rules: list[str] = []

        for rule in self.rules:
            try:
                fired = rule.condition(context)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Rule %s condition raised an error: %s", rule.id, exc
                )
                fired = False

            applied_rules.append(rule.id)

            if fired:
                try:
                    severity, message = rule.action(context)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Rule %s action raised an error: %s", rule.id, exc
                    )
                    severity, message = "warning", f"Rule {rule.id} action error: {exc}"

                prefixed_message = f"[{rule.id}] {message}"
                if severity == "violation":
                    violations.append(prefixed_message)
                    logger.info("Rule %s FIRED (violation): %s", rule.id, message)
                else:
                    warnings.append(prefixed_message)
                    logger.info("Rule %s FIRED (warning): %s", rule.id, message)

        passed = len(violations) == 0
        return RuleResult(
            passed=passed,
            violations=violations,
            warnings=warnings,
            applied_rules=applied_rules,
        )


# Singleton instance
rule_engine = RuleEngine()
