"""
Intent Recognizer Service for ILbuy Intent Service.

Uses a combination of:
1. Jieba tokenisation + keyword matching (primary signal)
2. TF-IDF + cosine similarity for soft scoring
3. Regex rule-based fallback patterns

All 15 IntentEnum values are fully supported.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Optional

import jieba
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.schemas import IntentEnum, IntentRecognizeResponse, SubIntentScore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword dictionary  —  intent → list of Chinese signal terms
# ---------------------------------------------------------------------------

INTENT_KEYWORDS: dict[IntentEnum, list[str]] = {
    IntentEnum.PURCHASE_INQUIRY: [
        "买", "购买", "入手", "想要", "需要", "订购", "下单", "采购",
        "要买", "想买", "打算买", "准备买", "求购", "选购",
    ],
    IntentEnum.PRICE_QUERY: [
        "价格", "多少钱", "价钱", "报价", "售价", "优惠", "折扣",
        "便宜", "贵", "费用", "花费", "要多少", "几块钱", "价位",
    ],
    IntentEnum.SPEC_QUERY: [
        "参数", "配置", "规格", "性能", "处理器", "内存", "屏幕",
        "摄像头", "电池", "尺寸", "重量", "分辨率", "像素", "芯片",
        "跑分", "频率", "核心", "接口", "材质",
    ],
    IntentEnum.COMPARISON: [
        "对比", "比较", "区别", "差异", "哪个好", "哪款好", "哪个更好",
        "还是", "和.*相比", "pk", "PK", "选哪个", "比.*好",
        "优劣", "差多少", "差别", "versus", "vs",
    ],
    IntentEnum.RECOMMENDATION: [
        "推荐", "帮我选", "选什么好", "什么好", "建议", "介绍",
        "求推荐", "有没有好的", "帮推荐", "给我推荐",
        "哪款合适", "适合我", "好用的", "值得买",
    ],
    IntentEnum.COMPLAINT: [
        "投诉", "举报", "不满意", "差评", "骗人", "虚假", "投诉你们",
        "太差了", "垃圾", "烂", "欺骗", "坑", "维权", "曝光",
    ],
    IntentEnum.AFTER_SALES: [
        "售后", "维修", "保修", "坏了", "故障", "问题", "修理",
        "报修", "质保", "换件", "维权", "修好", "上门维修",
    ],
    IntentEnum.LOGISTICS: [
        "物流", "快递", "发货", "到货", "运输", "配送", "几天到",
        "查物流", "快递单号", "包裹", "送达", "揽收", "派送",
    ],
    IntentEnum.RETURN: [
        "退货", "退款", "退回", "申请退", "7天无理由", "退掉",
        "不要了", "想退", "退换", "退", "退钱",
    ],
    IntentEnum.EXCHANGE: [
        "换货", "更换", "换一个", "换新", "以旧换新", "补发",
        "换成", "重新发", "发一个新的",
    ],
    IntentEnum.BUDGET_INQUIRY: [
        "预算", "多少钱以内", "千元", "万元", "元以内", "元以下",
        "百元", "不超过", "控制在", "最多花", "性价比",
    ],
    IntentEnum.BRAND_QUERY: [
        "品牌", "哪个牌子", "什么牌子", "牌子好", "国产", "进口",
        "哪家", "厂家", "厂商", "品牌推荐", "口碑",
    ],
    IntentEnum.CATEGORY_BROWSE: [
        "都有什么", "有哪些", "种类", "类型", "分类", "看看",
        "逛逛", "全部", "所有", "系列", "款式",
    ],
    IntentEnum.CUSTOM_ORDER: [
        "定制", "定做", "按需", "个性化", "专属", "特别定制",
        "私人定制", "批量", "企业采购", "大批量", "团购",
    ],
    IntentEnum.OTHER: [
        "你好", "在吗", "客服", "帮助", "问一下", "咨询",
        "谢谢", "感谢",
    ],
}

# ---------------------------------------------------------------------------
# Regex fallback patterns
# ---------------------------------------------------------------------------

INTENT_REGEX_PATTERNS: dict[IntentEnum, list[str]] = {
    IntentEnum.PRICE_QUERY: [
        r"多少\s*钱",
        r"[¥￥]?\d+\s*元",
        r"价格\s*[是怎么多少]",
    ],
    IntentEnum.BUDGET_INQUIRY: [
        r"预算\s*\d+",
        r"\d+\s*[万千百]?\s*元\s*以[内下]",
        r"不\s*超过\s*\d+",
    ],
    IntentEnum.LOGISTICS: [
        r"快递\s*单号",
        r"[几什么]\s*[天号]\s*[到能可]",
        r"发货\s*了\s*[吗么]",
    ],
    IntentEnum.RETURN: [
        r"退\s*[货款]",
        r"7\s*天\s*无\s*理\s*由",
        r"申请\s*退",
    ],
    IntentEnum.EXCHANGE: [
        r"换\s*[货一个新]",
        r"以旧换新",
    ],
    IntentEnum.COMPARISON: [
        r"([\u4e00-\u9fff\w]+)\s*[和跟与]\s*([\u4e00-\u9fff\w]+)\s*[哪个比较]",
        r"vs\.?\s*",
    ],
    IntentEnum.SPEC_QUERY: [
        r"\d+\s*[Gg][Bb]",
        r"\d+\s*[Mm][Hh][Zz]",
        r"\d+\s*[mM][aA][hH]",
        r"\d+\s*[iI]nch|英寸",
    ],
    IntentEnum.PURCHASE_INQUIRY: [
        r"(想|要|打算|准备)\s*(买|购买|入手|订)",
    ],
    IntentEnum.RECOMMENDATION: [
        r"(帮\s*[我]?\s*)?(推荐|建议|介绍)\s*[一几]?\s*[下款个台部]?",
        r"哪\s*[款个台]\s*[比较]*\s*好",
    ],
    IntentEnum.AFTER_SALES: [
        r"(坏|出\s*问\s*题|故\s*障)\s*了",
        r"[保质]\s*修",
    ],
    IntentEnum.COMPLAINT: [
        r"(投\s*诉|举\s*报)",
        r"(太|很|非常)\s*(差|烂|糟)",
    ],
    IntentEnum.CUSTOM_ORDER: [
        r"(定\s*制|定\s*做|批\s*量)",
        r"企业\s*采购",
    ],
    IntentEnum.BRAND_QUERY: [
        r"什么\s*牌\s*子",
        r"哪\s*个\s*品\s*牌",
    ],
    IntentEnum.CATEGORY_BROWSE: [
        r"都\s*有\s*[什么哪些]",
        r"有\s*哪\s*些\s*[款型]",
    ],
}


# ---------------------------------------------------------------------------
# TF-IDF corpus  — one representative sentence per intent for soft matching
# ---------------------------------------------------------------------------

INTENT_CORPUS: dict[IntentEnum, str] = {
    IntentEnum.PURCHASE_INQUIRY: "我想购买一台电子产品，打算下单入手",
    IntentEnum.PRICE_QUERY: "这个产品多少钱，价格是多少，有优惠折扣吗",
    IntentEnum.SPEC_QUERY: "这款产品的配置参数怎么样，处理器内存屏幕规格",
    IntentEnum.COMPARISON: "这两款产品对比区别哪个更好哪款值得选",
    IntentEnum.RECOMMENDATION: "帮我推荐一款合适的产品，给建议介绍值得买",
    IntentEnum.COMPLAINT: "投诉举报服务太差不满意维权",
    IntentEnum.AFTER_SALES: "售后维修保修故障坏了修理质保",
    IntentEnum.LOGISTICS: "物流快递发货配送几天到查快递单号",
    IntentEnum.RETURN: "退货退款申请退回七天无理由",
    IntentEnum.EXCHANGE: "换货更换换新以旧换新重新发货",
    IntentEnum.BUDGET_INQUIRY: "预算多少钱以内性价比不超过元以下",
    IntentEnum.BRAND_QUERY: "品牌哪个牌子好国产进口厂商口碑",
    IntentEnum.CATEGORY_BROWSE: "分类都有什么有哪些款式种类系列",
    IntentEnum.CUSTOM_ORDER: "定制定做批量采购企业个性化",
    IntentEnum.OTHER: "你好客服帮助咨询问一下",
}


class IntentRecognizer:
    """
    Chinese e-commerce intent recognizer.

    Uses three complementary methods:
    1. Keyword match scoring  (fast, deterministic)
    2. TF-IDF cosine similarity  (generalisation over unseen vocabulary)
    3. Regex pattern rules  (high-precision trigger patterns)
    """

    def __init__(self) -> None:
        self._tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self._corpus_matrix = None
        self._corpus_intents: list[IntentEnum] = []
        self._initialized = False
        # Compile all regex patterns once at startup
        self._compiled_regex: dict[IntentEnum, list[re.Pattern]] = {}
        for intent, patterns in INTENT_REGEX_PATTERNS.items():
            self._compiled_regex[intent] = [
                re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns
            ]

    def initialize(self) -> None:
        """Build TF-IDF index. Call once at service startup."""
        logger.info("Initialising IntentRecognizer TF-IDF index …")
        self._corpus_intents = list(INTENT_CORPUS.keys())
        corpus_texts = [
            " ".join(jieba.cut(INTENT_CORPUS[i])) for i in self._corpus_intents
        ]
        self._tfidf_vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(1, 3),
            sublinear_tf=True,
        )
        self._corpus_matrix = self._tfidf_vectorizer.fit_transform(corpus_texts)
        self._initialized = True
        logger.info("IntentRecognizer TF-IDF index ready (%d intents).", len(self._corpus_intents))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recognize(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> IntentRecognizeResponse:
        """
        Recognize the primary intent of the given Chinese text.

        Parameters
        ----------
        text:       Raw user utterance.
        context:    Optional conversation context dict.
        session_id: Opaque session identifier to echo back.

        Returns
        -------
        IntentRecognizeResponse with primary intent, confidence, and top-3 sub-intents.
        """
        if not self._initialized:
            self.initialize()

        scores: dict[IntentEnum, float] = defaultdict(float)

        # 1. Keyword match scoring
        kw_scores = self._keyword_score(text)
        for intent, score in kw_scores.items():
            scores[intent] += score * 0.50

        # 2. TF-IDF cosine similarity
        tfidf_scores = self._tfidf_score(text)
        for intent, score in tfidf_scores.items():
            scores[intent] += score * 0.35

        # 3. Regex rule bonuses
        regex_scores = self._regex_score(text)
        for intent, score in regex_scores.items():
            scores[intent] += score * 0.15

        # Context hint — boost intent if previous_intent exists
        if context and "previous_intent" in context:
            try:
                prev = IntentEnum(context["previous_intent"])
                scores[prev] += 0.05
            except ValueError:
                pass

        # Normalise so that all scores sum to 1
        total = sum(scores.values()) or 1.0
        normalised = {k: v / total for k, v in scores.items()}

        # Sort descending
        ranked = sorted(normalised.items(), key=lambda x: x[1], reverse=True)

        primary_intent, primary_confidence = ranked[0]
        # Cap confidence at 0.99 to avoid misleadingly certain outputs
        primary_confidence = min(primary_confidence, 0.99)

        sub_intents = [
            SubIntentScore(intent=intent, confidence=round(min(conf, 0.99), 4))
            for intent, conf in ranked[1:4]
        ]

        return IntentRecognizeResponse(
            intent=primary_intent,
            confidence=round(primary_confidence, 4),
            sub_intents=sub_intents,
            session_id=session_id,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> list[str]:
        """Jieba word segmentation."""
        return list(jieba.cut(text, cut_all=False))

    def _keyword_score(self, text: str) -> dict[IntentEnum, float]:
        """
        Return a score per intent based on keyword overlap.
        Score = matched_keywords / total_keywords_in_intent (normalised).
        """
        tokens = set(self._tokenize(text))
        # Also add raw text for short keyword matching
        raw_text = text

        scores: dict[IntentEnum, float] = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            matches = 0
            for kw in keywords:
                if kw in tokens or kw in raw_text:
                    matches += 1
            if matches > 0:
                scores[intent] = matches / len(keywords)
        return scores

    def _tfidf_score(self, text: str) -> dict[IntentEnum, float]:
        """Compute cosine similarity between user text and each intent corpus entry."""
        if self._tfidf_vectorizer is None or self._corpus_matrix is None:
            return {}

        tokenised = " ".join(jieba.cut(text))
        try:
            query_vec = self._tfidf_vectorizer.transform([tokenised])
        except Exception:
            return {}

        similarities = cosine_similarity(query_vec, self._corpus_matrix)[0]
        return {
            intent: float(sim)
            for intent, sim in zip(self._corpus_intents, similarities)
            if sim > 0
        }

    def _regex_score(self, text: str) -> dict[IntentEnum, float]:
        """Apply high-precision regex patterns and return binary hit scores."""
        scores: dict[IntentEnum, float] = {}
        for intent, patterns in self._compiled_regex.items():
            for pattern in patterns:
                if pattern.search(text):
                    # Each regex hit contributes a fixed bonus
                    scores[intent] = scores.get(intent, 0.0) + 0.5
                    break  # One hit per intent is sufficient for the bonus
        return scores
