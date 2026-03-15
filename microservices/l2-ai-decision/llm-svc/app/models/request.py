"""
大模型调用服务请求/响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from enum import Enum


class LLMProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    ERNIE = "ernie"


class CompletionRequest(BaseModel):
    """通用大模型补全请求"""
    prompt: str = Field(..., min_length=1, description="用户提示词")
    system_prompt: Optional[str] = Field(None, description="系统提示词（覆盖默认值）")
    provider: Optional[LLMProvider] = Field(None, description="指定模型提供商，不填使用默认")
    temperature: float = Field(0.3, ge=0.0, le=2.0, description="创意程度 0-2")
    max_tokens: int = Field(4096, ge=100, le=16000, description="最大输出Token数")


class ReportRequest(BaseModel):
    """采购决策报告生成请求（供 decision-svc 调用）"""
    user_type: str = Field(..., description="用户类型：B2B/B2C")
    brand_status: str = Field(..., description="品牌状态：decided/undecided")
    product_category: str = Field(..., description="商品类别")
    products_data: List[Any] = Field(..., description="评分后的候选商品数据")
    user_requirements: dict = Field(default_factory=dict, description="用户需求参数")
    provider: Optional[LLMProvider] = Field(None, description="指定模型提供商")


class CompletionResponse(BaseModel):
    """通用补全响应"""
    content: str = Field(..., description="模型输出内容")
    provider: str = Field(..., description="实际使用的模型提供商")
    model: str = Field(..., description="模型名称")
    usage: Optional[dict] = Field(None, description="Token用量统计")


class ReportResponse(BaseModel):
    """采购报告响应"""
    report: str = Field(..., description="Markdown格式采购决策报告")
    provider: str = Field(..., description="实际使用的模型提供商")
