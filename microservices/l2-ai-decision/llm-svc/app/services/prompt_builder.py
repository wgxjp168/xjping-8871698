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

_SCORING_INSIGHT_SYSTEM = (
    _BASE_SYSTEM
    + "\n\n你是采购决策评分专家，需对各评分维度进行定性分析，识别规则引擎无法捕获的"
    "市场信号、品牌信誉和情境风险。"
    "\n\n请以JSON格式输出评分洞察，结构如下：\n"
    '{"dimension_insights": [{"dimension": "维度名", "signal": "positive|negative|neutral", '
    '"adjustment": -5.0, "rationale": "原因...", "confidence": 0.85}], '
    '"risk_signals": ["风险1", "风险2"], "opportunity_signals": ["机会1"], '
    '"overall_assessment": "综合评估...", "adjusted_total": 72.5}'
)

_INTENT_DISAMBIGUATION_SYSTEM = (
    _BASE_SYSTEM
    + "\n\n你是用户意图理解专家，专注于电商采购场景的意图识别。"
    "当规则引擎对用户意图置信度较低时，你需要结合上下文对意图进行精准判断。"
    "\n\n请以JSON格式输出消歧结果：\n"
    '{"intent": "意图枚举值", "confidence": 0.92, '
    '"rationale": "判断理由...", '
    '"sub_intents": [{"intent": "次要意图", "confidence": 0.3}]}'
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

    # ------------------------------------------------------------------
    # Scoring insight  (NEW)
    # Asks the LLM to evaluate dimension signals missed by rule-based models.
    # ------------------------------------------------------------------

    @staticmethod
    def build_scoring_insight_prompt(
        scoring_context: str,
        intent: str,
        entities: Dict[str, Any],
        dimension_scores: Dict[str, float],
        enriched_context: Dict[str, Any],
    ) -> List[ChatMessage]:
        """
        Build a prompt for LLM to assess qualitative purchase signals and
        suggest per-dimension score adjustments.

        Parameters
        ----------
        scoring_context:   'B2B' | 'B2C_KNOWN' | 'B2C_UNKNOWN'
        intent:            User purchase intent string.
        entities:          Extracted entities (brand, category, budget, specs…).
        dimension_scores:  Current rule-based dimension scores (0-100).
        enriched_context:  Product / market data from L3 services.
        """
        user_content = (
            "请对以下采购场景的各评分维度进行定性分析，识别规则引擎可能遗漏的市场信号。\n\n"
            f"**评分场景**：{scoring_context}\n\n"
            f"**用户意图**：{intent}\n\n"
            f"**识别实体**：\n{json.dumps(entities, ensure_ascii=False, indent=2)}\n\n"
            f"**当前规则评分**（0-100分）：\n"
            f"{json.dumps(dimension_scores, ensure_ascii=False, indent=2)}\n\n"
            f"**产品与市场数据**：\n{json.dumps(enriched_context, ensure_ascii=False, indent=2)}\n\n"
            "基于上述信息，请：\n"
            "1. 对每个评分维度给出定性洞察（正向/负向/中性），以及建议调整分值（-20~+20）\n"
            "2. 列出主要风险信号（3条以内）\n"
            "3. 列出主要机会信号（3条以内）\n"
            "4. 给出综合评估（100字以内）\n"
            "5. 基于调整建议，给出调整后的综合分（0-100）\n\n"
            "以JSON格式输出，adjustment字段为浮点数，正值表示加分，负值表示减分。"
        )

        return [
            ChatMessage(role="system", content=_SCORING_INSIGHT_SYSTEM),
            ChatMessage(role="user", content=user_content),
        ]

    # ------------------------------------------------------------------
    # Intent disambiguation  (NEW)
    # Resolves low-confidence intent classification ambiguity via LLM.
    # ------------------------------------------------------------------

    @staticmethod
    def build_intent_disambiguation_prompt(
        text: str,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[ChatMessage]:
        """
        Build a prompt for LLM to disambiguate among top-N intent candidates.

        Parameters
        ----------
        text:        Original user utterance.
        candidates:  List of {'intent': str, 'confidence': float} dicts,
                     ordered by descending rule-based confidence.
        context:     Conversation context (previous_intent, entities, session_id…).
        """
        candidates_str = json.dumps(candidates, ensure_ascii=False, indent=2)
        context_str = json.dumps(context, ensure_ascii=False, indent=2)

        # Enumerate known intent values inline so the LLM picks from the correct set
        known_intents = (
            "PURCHASE_INQUIRY, PRICE_QUERY, SPEC_QUERY, COMPARISON, "
            "RECOMMENDATION, COMPLAINT, AFTER_SALES, LOGISTICS, RETURN, "
            "EXCHANGE, BUDGET_INQUIRY, BRAND_QUERY, CATEGORY_BROWSE, "
            "CUSTOM_ORDER, OTHER"
        )

        user_content = (
            "以下是用户在电商采购场景下的原始话语，规则引擎识别置信度较低，需要你进行意图消歧。\n\n"
            f"**用户话语**：{text}\n\n"
            f"**规则引擎候选意图**（置信度从高到低）：\n{candidates_str}\n\n"
            f"**对话上下文**：\n{context_str}\n\n"
            f"**可选意图枚举**：{known_intents}\n\n"
            "请综合用户话语的语义、上下文和候选意图，选择最准确的意图，"
            "并说明理由。intent字段必须是上述枚举值之一，confidence范围0.0-1.0。"
        )

        return [
            ChatMessage(role="system", content=_INTENT_DISAMBIGUATION_SYSTEM),
            ChatMessage(role="user", content=user_content),
        ]
