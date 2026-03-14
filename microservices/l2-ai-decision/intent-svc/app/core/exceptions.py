"""
全局异常处理
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class IntentException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(IntentException)
    async def intent_exception_handler(request: Request, exc: IntentException):
        return JSONResponse(
            status_code=exc.code,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"系统异常: {str(exc)}", "data": None},
        )
