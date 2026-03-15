"""
定时/实时采集调度器
====================
使用 APScheduler（AsyncIOScheduler）管理：
  - 定时采集任务（cron）
  - 异步即时采集 job 执行
  - Job 状态跟踪 + 超时保护
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.models.schemas import (
    CrawlBatchResult, CrawlFilters, CrawlJobResponse, CrawlRequest,
    CrawlResult, CrawlStatus, Platform,
)
from app.services.platforms import get_adapter

logger = logging.getLogger(__name__)
settings = get_settings()


class JobRecord:
    __slots__ = ("job_id", "session_id", "status", "created_at", "updated_at",
                 "result", "error", "task")

    def __init__(self, job_id: str, session_id: str) -> None:
        self.job_id     = job_id
        self.session_id = session_id
        self.status     = CrawlStatus.PENDING
        self.created_at = time.time()
        self.updated_at = time.time()
        self.result: Optional[CrawlBatchResult] = None
        self.error:  Optional[str] = None
        self.task:   Optional[asyncio.Task] = None


class CrawlScheduler:
    """Manages crawl jobs and scheduled tasks."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
        self._jobs: Dict[str, JobRecord] = {}
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._scheduler.start()
        logger.info('"Crawl scheduler started"')

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info('"Crawl scheduler stopped"')

    # ── On-demand crawl ───────────────────────────────────────────────────

    async def submit_crawl(self, request: CrawlRequest) -> CrawlJobResponse:
        job_id = str(uuid.uuid4())
        record = JobRecord(job_id=job_id, session_id=request.session_id)
        self._jobs[job_id] = record

        record.task = asyncio.create_task(
            self._run_crawl(job_id, request),
            name=f"crawl-{job_id[:8]}",
        )
        record.task.add_done_callback(lambda t: self._on_done(job_id, t))

        return CrawlJobResponse(
            job_id=job_id,
            session_id=request.session_id,
            status=CrawlStatus.PENDING,
            message="Crawl job submitted",
        )

    def get_job_status(self, job_id: str) -> Optional[JobRecord]:
        return self._jobs.get(job_id)

    def list_active_jobs(self) -> List[Dict]:
        return [
            {"job_id": r.job_id, "status": r.status, "session_id": r.session_id}
            for r in self._jobs.values()
            if r.status in (CrawlStatus.PENDING, CrawlStatus.RUNNING)
        ]

    # ── Scheduled tasks ───────────────────────────────────────────────────

    def register_scheduled_task(
        self,
        name: str,
        cron_expr: str,
        keywords: List[str],
        platforms: List[Platform],
        filters: CrawlFilters,
        max_results: int = 50,
    ) -> str:
        trigger = CronTrigger.from_crontab(cron_expr, timezone=settings.scheduler_timezone)

        async def _task():
            req = CrawlRequest(
                session_id=f"scheduled-{name}",
                keywords=keywords,
                platforms=platforms,
                filters=filters,
                max_results_per_platform=max_results,
            )
            await self.submit_crawl(req)

        job = self._scheduler.add_job(_task, trigger=trigger, id=name, replace_existing=True)
        logger.info('"Scheduled task registered: name=%s cron=%s"', name, cron_expr)
        return job.id

    def list_scheduled_tasks(self) -> List[Dict]:
        return [
            {
                "id":      job.id,
                "next_run": str(job.next_run_time),
                "trigger":  str(job.trigger),
            }
            for job in self._scheduler.get_jobs()
        ]

    # ── Internal ─────────────────────────────────────────────────────────

    async def _run_crawl(self, job_id: str, request: CrawlRequest) -> None:
        record = self._jobs[job_id]
        record.status = CrawlStatus.RUNNING
        record.updated_at = time.time()
        t0 = time.time()

        async with self._semaphore:
            try:
                results = await asyncio.wait_for(
                    self._crawl_all_platforms(job_id, request),
                    timeout=settings.job_timeout_s,
                )
                total = sum(len(r.products) for r in results)
                successes = sum(1 for r in results if r.success)
                failures  = len(results) - successes

                batch = CrawlBatchResult(
                    job_id          = job_id,
                    session_id      = request.session_id,
                    results         = results,
                    total_products  = total,
                    success_count   = successes,
                    fail_count      = failures,
                    duration_ms     = int((time.time() - t0) * 1000),
                )
                record.result = batch
                record.status = CrawlStatus.COMPLETED
                logger.info(
                    '"Crawl job %s completed: %d products from %d platforms"',
                    job_id[:8], total, len(results),
                )

                # Forward to ETL service
                if request.callback_url or settings.etl_svc_url:
                    await self._forward_to_etl(batch, request.callback_url)

            except asyncio.TimeoutError:
                record.error  = "Job timed out"
                record.status = CrawlStatus.FAILED
                logger.error('"Crawl job %s timed out"', job_id[:8])
            except Exception as exc:
                record.error  = str(exc)
                record.status = CrawlStatus.FAILED
                logger.error('"Crawl job %s failed: %s"', job_id[:8], exc)
            finally:
                record.updated_at = time.time()

    async def _crawl_all_platforms(
        self, job_id: str, request: CrawlRequest,
    ) -> List[CrawlResult]:
        tasks = []
        for platform in request.platforms:
            for keyword in request.keywords:
                tasks.append(
                    self._crawl_single(job_id, platform, keyword, request)
                )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, CrawlResult)]

    async def _crawl_single(
        self,
        job_id: str,
        platform: Platform,
        keyword: str,
        request: CrawlRequest,
    ) -> CrawlResult:
        t0 = time.time()
        try:
            adapter = get_adapter(platform)
            products = await adapter.search(
                keyword=keyword,
                max_results=request.max_results_per_platform,
                filters=request.filters,
                session_id=request.session_id,
                job_id=job_id,
            )
            return CrawlResult(
                job_id      = job_id,
                session_id  = request.session_id,
                platform    = platform,
                keyword     = keyword,
                products    = products,
                total_found = len(products),
                success     = True,
                duration_ms = int((time.time() - t0) * 1000),
            )
        except Exception as exc:
            logger.error('"Crawl failed: platform=%s keyword=%s: %s"', platform.value, keyword, exc)
            return CrawlResult(
                job_id      = job_id,
                session_id  = request.session_id,
                platform    = platform,
                keyword     = keyword,
                products    = [],
                total_found = 0,
                success     = False,
                error       = str(exc),
                duration_ms = int((time.time() - t0) * 1000),
            )

    async def _forward_to_etl(
        self, batch: CrawlBatchResult, callback_url: Optional[str],
    ) -> None:
        url = callback_url or f"{settings.etl_svc_url}/etl/process"
        all_products = [p for r in batch.results for p in r.products]
        payload = {
            "job_id":       batch.job_id,
            "session_id":   batch.session_id,
            "raw_products": [p.model_dump(mode="json") for p in all_products],
            "deduplicate":  True,
            "normalize":    True,
            "compute_scores": True,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            logger.info('"Forwarded %d products to ETL"', len(all_products))
        except Exception as exc:
            logger.error('"Failed to forward to ETL: %s"', exc)

    def _on_done(self, job_id: str, task: asyncio.Task) -> None:
        if task.cancelled():
            record = self._jobs.get(job_id)
            if record:
                record.status = CrawlStatus.CANCELLED


# Singleton
crawl_scheduler = CrawlScheduler()
