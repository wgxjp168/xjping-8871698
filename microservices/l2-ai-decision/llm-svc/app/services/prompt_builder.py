"""
PromptBuilder – constructs Chinese-language prompts for every LLM use-case.

All system prompts adopt an ILbuy professional B2B/B2C e-commerce
consulting persona.  User turns are structured JSON-augmented Chinese text
so the model always has enough context to produce actionable responses.
"""

import json
from typing import Any, Dict, List, Optional

from app.models.schemas import ChatMessage


# ---------------------------------------------------------------------------
# Shared system prompt constants
# ---------------------------------------------------------------------------

_BASE_SYSTEM = (
    "你是ILbuy智能采购助手，专业的B2B/B2C电商决策顾问。"
    "你拥有丰富的供应链、产品采购和市场分析经验，能够为用户提供精准、"
    "专业的采购建议和决策支持。"
    "请始终以结构化、清晰的方式回复，语言简洁专业，避免冗余表达。"
    "在分析时，综合考虑产品质量、价格、供应商信誉、交货时效和合规要求等关键因素。"
)

_PRODUCT_ANALYSIS_SYSTEM = (
    _BASE_SYSTEM
    + "\n\n在进行产品分析时，请严格按照以下JSON格式输出分析结果，确保每个字段都有实质性内容：\n"
    '{"analysis": "综合分析...", "key_features": ["特性1", "特性2"], '
    '"pros": ["优势1", "优势2"], "cons": ["劣势1", "劣势2"], '
    '"match_score": 0.85, "recommendation": "最终建议..."}'
)

_DECISION_SUPPORT_SYSTEM = (
    _BASE_SYSTEM
    + "\n\n在提供决策支持时，请严格按照以下JSON格式输出，确保建议具有可操作性：\n"
    '{"decision_context": "决策背景...", '
    '"suggested_questions": ["问题1?", "问题2?"], '
    '"confidence_factors": ["因素1", "因素2"], '
    '"preliminary_recommendation": "初步建议..."}'
)

_REPORT_GENERATION_SYSTEM = (
    _BASE_SYSTEM
    + "\n\n请生成结构完整的采购决策报告，包括：执行摘要、需求分析、产品评估、"
    "供应商对比、风险评估和最终建议。报告须客观、数据驱动、结论明确。"
)

_SPEC_EXTRACTION_SYSTEM = (
    _BASE_SYSTEM
    + "\n\n请从提供的文本中提取结构化产品规格信息，以JSON格式输出，"
    "包含型号、规格参数、认证要求、包装信息等字段。"
    "如信息不全，相应字段填null。"
)


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------


class PromptBuilder:
    """Builds typed ChatMessage lists for each LLM task type."""

    # ------------------------------------------------------------------
    # Product analysis
    # ------------------------------------------------------------------

    @staticmethod
    def build_product_analysis_prompt(
        product_desc: str,
        requirements: Dict[str, Any],
        budget: Optional[Dict[str, Any]] = None,
    ) -> List[ChatMessage]:
        """
        Build a prompt asking the LLM to analyse a product against buyer
        requirements and return a structured JSON response.
        """
        budget_section = ""
        if budget:
            budget_section = f"\n\n**预算范围**：\n{json.dumps(budget, ensure_ascii=False, indent=2)}"

        user_content = (
            f"请对以下产品进行全面的采购分析。\n\n"
            f"**产品描述**：\n{product_desc}\n\n"
            f"**买家需求**：\n{json.dumps(requirements, ensure_ascii=False, indent=2)}"
            f"{budget_section}\n\n"
            "请根据买家需求评估产品的适配程度，以JSON格式输出分析结果，"
            "match_score范围为0.0-1.0（1.0表示完全匹配）。"
        )

        return [
            ChatMessage(role="system", content=_PRODUCT_ANALYSIS_SYSTEM),
            ChatMessage(role="user", content=user_content),
        ]

    # ------------------------------------------------------------------
    # Decision support
    # ------------------------------------------------------------------

    @staticmethod
    def build_decision_support_prompt(
        intent: str,
        entities: Dict[str, Any],
        brand_status: str,
        context: Dict[str, Any],
    ) -> List[ChatMessage]:
        """
        Build a prompt for generating a decision-support context, follow-up
        questions, and a preliminary recommendation based on the user's
        parsed intent and session context.
        """
        user_content = (
            "请为以下采购决策场景提供智能决策支持。\n\n"
            f"**用户意图**：{intent}\n\n"
            f"**识别实体**：\n{json.dumps(entities, ensure_ascii=False, indent=2)}\n\n"
            f"**品牌状态**：{brand_status}\n\n"
            f"**用户上下文**：\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
            "请综合以上信息，提供决策上下文、澄清问题列表（3-5个）、"
            "置信度影响因素和初步采购建议，以JSON格式输出。"
        )

        return [
            ChatMessage(role="system", content=_DECISION_SUPPORT_SYSTEM),
            ChatMessage(role="user", content=user_content),
        ]

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    @staticmethod
    def build_report_generation_prompt(
        decision_data: Dict[str, Any],
        scoring_result: Dict[str, Any],
    ) -> List[ChatMessage]:
        """
        Build a prompt for generating a comprehensive procurement decision
        report combining decision data and scoring results.
        """
        user_content = (
            "请根据以下采购决策数据和评分结果，生成一份完整的采购决策报告。\n\n"
            f"**决策数据**：\n{json.dumps(decision_data, ensure_ascii=False, indent=2)}\n\n"
            f"**评分结果**：\n{json.dumps(scoring_result, ensure_ascii=False, indent=2)}\n\n"
            "报告应包含以下章节：\n"
            "1. 执行摘要（核心结论，200字以内）\n"
            "2. 需求分析（买家需求解读）\n"
            "3. 产品评估（基于评分的详细分析）\n"
            "4. 供应商/产品对比（如有多个选项）\n"
            "5. 风险评估（主要采购风险及缓解措施）\n"
            "6. 最终建议（明确的行动建议）\n\n"
            "请以专业报告格式输出，语言简洁、数据支撑、结论清晰。"
        )

        return [
            ChatMessage(role="system", content=_REPORT_GENERATION_SYSTEM),
            ChatMessage(role="user", content=user_content),
        ]

    # ------------------------------------------------------------------
    # Spec extraction
    # ------------------------------------------------------------------

    @staticmethod
    def build_spec_extraction_prompt(text: str) -> List[ChatMessage]:
        """
        Build a prompt for extracting structured product specifications
        from unstructured text (listings, PDFs, emails…).
        """
        user_content = (
            "请从以下文本中提取结构化的产品规格信息。\n\n"
            f"**原始文本**：\n{text}\n\n"
            "请以JSON格式输出，包含以下字段（不适用时填null）：\n"
            "- model_number：型号\n"
            "- specifications：规格参数（嵌套对象）\n"
            "- certifications：认证要求（列表）\n"
            "- packaging：包装信息\n"
            "- material：材质\n"
            "- dimensions：尺寸\n"
            "- weight：重量\n"
            "- color_options：颜色选项（列表）\n"
            "- min_order_quantity：最小起订量\n"
            "- lead_time：交货期\n"
            "- other_attributes：其他属性（嵌套对象）"
        )

        return [
            ChatMessage(role="system", content=_SPEC_EXTRACTION_SYSTEM),
            ChatMessage(role="user", content=user_content),
        ]
