from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db

router = APIRouter(tags=["health"])

@router.get("/health/liveness")
async def liveness():
    return {"status": "UP"}

@router.get("/health/readiness")
async def readiness(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "UP", "db": "UP"}
    except Exception as e:
        return {"status": "DOWN", "db": str(e)}, 503

@router.get("/actuator/health/liveness")
async def actuator_liveness():
    return {"status": "UP"}

@router.get("/actuator/health/readiness")
async def actuator_readiness(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "UP"}
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "DOWN"})

