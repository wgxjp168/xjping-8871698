"""
决策编排服务请求/响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class InputMode(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    LINK = "link"
    VOICE = "voice"


class DecisionRequest(BaseModel):
    """采购决策请求"""
    session_id: str = Field(..., description="会话ID，用于关联多轮对话")
    user_id: str = Field(..., description="用户ID")
    input_mode: InputMode = Field(InputMode.TEXT, description="输入方式")
    content: str = Field(..., min_length=2, description="用户输入的采购需求描述")
    image_url: Optional[str] = Field(None, description="商品图片URL（图片模式）")
    link_url: Optional[str] = Field(None, description="商品链接（链接模式）")
    history: Optional[List[dict]] = Field(default_factory=list, description="多轮对话历史")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "user_id": "user_001",
                "input_mode": "text",
                "content": "我想买一台华为MatePad，预算3000元，主要用来办公",
            }
        }


class ClarificationRequest(BaseModel):
    """追问补充请求"""
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    answer: str = Field(..., description="用户对追问的回答")
    original_content: str = Field(..., description="原始需求描述")
