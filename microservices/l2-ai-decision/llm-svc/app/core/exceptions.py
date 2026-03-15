"""
大模型调用服务全局异常处理
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class LLMException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class ProviderUnavailableError(LLMException):
    def __init__(self, provider: str):
        super().__init__(503, f"模型提供商 [{provider}] 暂时不可用，请稍后重试")


class TokenLimitExceededError(LLMException):
    def __init__(self):
        super().__init__(400, "输入内容过长，请缩短后重试")


class InvalidProviderError(LLMException):
    def __init__(self, provider: str):
        super().__init__(400, f"不支持的模型提供商: {provider}")


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(LLMException)
    async def llm_exception_handler(request: Request, exc: LLMException):
        logger.warning("LLM业务异常: code=%s msg=%s", exc.code, exc.message)
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
