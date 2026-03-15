"""Structured JSON logging setup."""
from __future__ import annotations

import logging
import sys

from app.core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    fmt = (
        '{"time":"%(asctime)s","level":"%(levelname)s",'
        '"service":"crawler-svc","logger":"%(name)s","msg":%(message)s}'
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "scrapy", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
