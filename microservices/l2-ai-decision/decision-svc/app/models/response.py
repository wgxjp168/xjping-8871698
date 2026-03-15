"""
决策编排服务响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class RecommendationLevel(str, Enum):
    QUALITY = "品质款"
    VALUE = "性价比款"
    NOT_RECOMMENDED = "不推荐"


class ProductRecommendation(BaseModel):
    """单个商品推荐结果"""
    product_id: str = Field(..., description="商品ID")
    title: str = Field(..., description="商品标题")
    price: float = Field(..., description="价格（元）")
    platform: str = Field(..., description="来源平台")
    product_url: Optional[str] = Field(None, description="商品链接")
    image_url: Optional[str] = Field(None, description="商品图片")

    # 评分维度
    total_score: float = Field(..., description="综合评分 0-100")
    dimension_scores: Dict[str, float] = Field(..., description="各维度分项评分")
    recommendation_level: RecommendationLevel = Field(..., description="推荐级别")
    score_reason: str = Field(..., description="评分说明")

    # 核心属性
    sales_volume: int = Field(0, description="销量")
    rating: float = Field(0.0, description="用户评分 1-5")
    review_count: int = Field(0, description="评价数")
    shop_name: Optional[str] = Field(None, description="店铺名称")
    is_official: bool = Field(False, description="是否官方旗舰店")


class IntentSummary(BaseModel):
    """意图分析摘要（对外展示用）"""
    user_type: str = Field(..., description="用户类型：B2B/B2C")
    brand_status: str = Field(..., description="品牌状态：decided/undecided")
    product_category: str = Field(..., description="商品类别")
    extracted_params: Dict[str, Any] = Field(default_factory=dict, description="提取参数")
    confidence: float = Field(..., description="识别置信度")


class DecisionStatus(str, Enum):
    SUCCESS = "success"                # 完整决策报告
    NEED_CLARIFICATION = "need_clarification"  # 需要追问
    PARTIAL = "partial"                # 部分结果（数据不足）
    ERROR = "error"                    # 决策失败


class DecisionResponse(BaseModel):
    """采购决策响应"""
    session_id: str
    user_id: str
    status: DecisionStatus = Field(..., description="决策状态")

    # 意图分析
    intent: Optional[IntentSummary] = Field(None, description="意图分析结果")

    # 追问（status=need_clarification 时有值）
    clarification_questions: Optional[List[str]] = Field(None, description="追问问题")

    # 推荐结果（status=success 时有值）
    recommendations: Optional[List[ProductRecommendation]] = Field(
        None, description="推荐商品列表（按综合评分降序）"
    )
    quality_pick: Optional[ProductRecommendation] = Field(
        None, description="品质款首选"
    )
    value_pick: Optional[ProductRecommendation] = Field(
        None, description="性价比款首选"
    )

    # AI生成报告
    report: Optional[str] = Field(None, description="AI采购决策报告（Markdown格式）")

    # 元数据
    processing_time_ms: int = Field(0, description="处理耗时（毫秒）")
    data_sources: List[str] = Field(default_factory=list, description="数据来源平台")
    created_at: datetime = Field(default_factory=datetime.now, description="生成时间")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "user_id": "user_001",
                "status": "success",
                "intent": {
                    "user_type": "B2C",
                    "brand_status": "decided",
                    "product_category": "平板电脑",
                    "extracted_params": {"brand": "华为", "budget": 3000.0},
                    "confidence": 0.92,
                },
                "recommendations": [],
                "processing_time_ms": 1850,
            }
        }
