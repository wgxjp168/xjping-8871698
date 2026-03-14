"""
意图识别请求/响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class InputMode(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    LINK = "link"
    VOICE = "voice"


class UserType(str, Enum):
    B2B = "B2B"   # 企业采购
    B2C = "B2C"   # 个人消费


class BrandStatus(str, Enum):
    DECIDED = "decided"       # 已定品牌
    UNDECIDED = "undecided"   # 未定品牌


class IntentRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    input_mode: InputMode = Field(InputMode.TEXT, description="输入方式")
    content: str = Field(..., description="用户输入内容")
    image_url: Optional[str] = Field(None, description="图片URL（图片输入时）")
    link_url: Optional[str] = Field(None, description="商品链接（链接输入时）")
    history: Optional[List[dict]] = Field(default_factory=list, description="历史对话")


class ExtractedParams(BaseModel):
    material: Optional[str] = Field(None, description="材质")
    size: Optional[str] = Field(None, description="尺寸规格")
    capacity: Optional[str] = Field(None, description="容量")
    power: Optional[str] = Field(None, description="功率")
    color: Optional[str] = Field(None, description="颜色")
    quantity: Optional[int] = Field(None, description="采购数量（B2B）")
    budget: Optional[float] = Field(None, description="预算（元）")
    brand: Optional[str] = Field(None, description="品牌名称")
    category: Optional[str] = Field(None, description="商品类别")
    other: Optional[dict] = Field(default_factory=dict, description="其他参数")


class IntentResponse(BaseModel):
    session_id: str
    user_type: UserType = Field(..., description="用户类型：B2B/B2C")
    brand_status: BrandStatus = Field(..., description="品牌状态：已定/未定")
    product_category: str = Field(..., description="识别到的商品类别")
    extracted_params: ExtractedParams = Field(..., description="提取的结构化参数")
    confidence: float = Field(..., description="识别置信度 0-1")
    need_clarification: bool = Field(False, description="是否需要追问")
    clarification_questions: Optional[List[str]] = Field(None, description="追问问题列表")
    raw_intent: str = Field(..., description="原始意图描述")
