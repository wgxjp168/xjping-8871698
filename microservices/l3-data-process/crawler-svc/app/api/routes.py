"""
crawler-svc API routes
======================
Endpoints:
  POST /crawl/search          — on-demand crawl triggered by L2 decision-svc
  GET  /crawl/jobs/{job_id}   — poll job status
  POST /crawl/schedule        — register scheduled recurring crawl
  GET  /crawl/schedule        — list scheduled tasks
  DELETE /crawl/schedule/{id} — remove scheduled task
  POST /proxy/add             — add a proxy to the pool
  GET  /proxy/stats           — proxy pool statistics
  GET  /compliance/report     — robots.txt compliance status
  GET  /info                  — platform + system status
  GET  /health                — health check
"""
from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.models.schemas import (
    CrawlJobResponse, CrawlRequest, HealthResponse,
    Platform, PlatformStatus, ScheduledCrawlRequest, ServiceInfo,
)
from app.services.api_manager import api_manager
from app.services.compliance_monitor import compliance_monitor
from app.services.platforms import all_adapters
from app.services.proxy_manager import proxy_manager
from app.services.scheduler import crawl_scheduler

router = APIRouter()
settings = get_settings()

_start_time = time.monotonic()


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["ops"])
async def health():
    return HealthResponse(
        status="ok",
        uptime_s=round(time.monotonic() - _start_time, 1),
    )


# ── Crawl ─────────────────────────────────────────────────────────────────────

@router.post(
    "/crawl/search",
    response_model=CrawlJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["crawl"],
    summary="Submit on-demand crawl (called by L2 decision-svc)",
)
async def submit_crawl(request: CrawlRequest) -> CrawlJobResponse:
    """
    Accepts a crawl request from L2 decision-svc.  Immediately returns a
    job_id; caller polls /crawl/jobs/{job_id} or receives results via
    callback_url when the job completes.
    """
    return await crawl_scheduler.submit_crawl(request)


@router.get("/crawl/jobs/{job_id}", tags=["crawl"], summary="Poll job status")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    record = crawl_scheduler.get_job_status(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    resp: Dict[str, Any] = {
        "job_id":     record.job_id,
        "session_id": record.session_id,
        "status":     record.status,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "error":      record.error,
    }
    if record.result:
        r = record.result
        resp["summary"] = {
            "total_products": r.total_products,
            "success_count":  r.success_count,
            "fail_count":     r.fail_count,
            "duration_ms":    r.duration_ms,
            "platforms":      [res.platform for res in r.results],
        }
    return resp


@router.get("/crawl/jobs", tags=["crawl"], summary="List active jobs")
async def list_active_jobs():
    return {"jobs": crawl_scheduler.list_active_jobs()}


# ── Scheduled tasks ───────────────────────────────────────────────────────────

@router.post("/crawl/schedule", tags=["schedule"], summary="Register recurring crawl")
async def register_schedule(request: ScheduledCrawlRequest) -> Dict[str, str]:
    task_id = crawl_scheduler.register_scheduled_task(
        name        = request.name,
        cron_expr   = request.cron_expr,
        keywords    = request.keywords,
        platforms   = request.platforms,
        filters     = request.filters,
        max_results = request.max_results_per_platform,
    )
    return {"task_id": task_id, "status": "registered", "cron": request.cron_expr}


@router.get("/crawl/schedule", tags=["schedule"], summary="List scheduled tasks")
async def list_schedules():
    return {"tasks": crawl_scheduler.list_scheduled_tasks()}


@router.delete("/crawl/schedule/{task_id}", tags=["schedule"])
async def delete_schedule(task_id: str):
    from app.services.scheduler import crawl_scheduler as sched
    job = sched._scheduler.get_job(task_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    job.remove()
    return {"task_id": task_id, "status": "removed"}


# ── Proxy management ──────────────────────────────────────────────────────────

class AddProxyRequest(BaseModel):
    host:     str
    port:     int
    protocol: str = "http"
    username: str = ""
    password: str = ""


@router.post("/proxy/add", tags=["proxy"], summary="Add proxy to pool")
async def add_proxy(req: AddProxyRequest):
    record = await proxy_manager.add_proxy(
        host=req.host, port=req.port, protocol=req.protocol,
        username=req.username or None, password=req.password or None,
    )
    return {"status": "added", "proxy": f"{req.host}:{req.port}"}


@router.get("/proxy/stats", tags=["proxy"], summary="Proxy pool stats")
async def proxy_stats():
    return proxy_manager.pool_stats()


# ── Compliance ────────────────────────────────────────────────────────────────

@router.get("/compliance/report", tags=["compliance"])
async def compliance_report():
    return await compliance_monitor.compliance_report()


# ── Service info ──────────────────────────────────────────────────────────────

@router.get("/info", response_model=ServiceInfo, tags=["ops"])
async def service_info() -> ServiceInfo:
    platform_statuses = []
    rpm_map = {
        Platform.TAOBAO: settings.taobao_rpm,
        Platform.JD:     settings.jd_rpm,
        Platform.ALI1688: settings.ali1688_rpm,
        Platform.PDD:    settings.pdd_rpm,
        Platform.VIPSHOP: settings.vipshop_rpm,
        Platform.SUNING: settings.suning_rpm,
        Platform.DOUYIN: settings.douyin_rpm,
    }
    for p in Platform:
        platform_statuses.append(PlatformStatus(
            platform           = p,
            enabled            = True,
            rate_limit_rpm     = rpm_map.get(p, 30),
            current_rpm        = api_manager.get_platform_rpm(p),
            proxy_required     = settings.proxy_enabled,
            compliance_status  = api_manager.get_breaker_state(p),
        ))

    return ServiceInfo(
        platforms       = platform_statuses,
        proxy_pool_size = proxy_manager.pool_size(),
        active_jobs     = len(crawl_scheduler.list_active_jobs()),
        scheduled_tasks = len(crawl_scheduler.list_scheduled_tasks()),
    )
