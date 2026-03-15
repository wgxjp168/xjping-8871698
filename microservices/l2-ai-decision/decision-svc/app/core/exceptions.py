"""
决策编排服务全局异常处理
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class DecisionException(Exception):
    """业务异常基类"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class IntentServiceError(DecisionException):
    """意图识别服务调用失败"""
    def __init__(self, detail: str = "意图识别服务不可用"):
        super().__init__(503, detail)


class LLMServiceError(DecisionException):
    """大模型服务调用失败"""
    def __init__(self, detail: str = "大模型服务不可用"):
        super().__init__(503, detail)


class DataCollectError(DecisionException):
    """数据采集失败"""
    def __init__(self, detail: str = "商品数据采集失败"):
        super().__init__(502, detail)


class DecisionTimeoutError(DecisionException):
    """决策超时"""
    def __init__(self):
        super().__init__(408, "决策处理超时，请稍后重试")


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(DecisionException)
    async def decision_exception_handler(request: Request, exc: DecisionException):
        logger.warning("决策业务异常: code=%s msg=%s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.code,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("未捕获异常: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"系统异常: {str(exc)}", "data": None},
        )
