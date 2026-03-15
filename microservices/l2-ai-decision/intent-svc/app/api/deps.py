"""
FastAPI dependency providers for ILbuy Intent Service.

All service objects are singletons created at first access and cached
via functools.lru_cache.  This avoids expensive re-initialisation on
every request while remaining compatible with FastAPI's Depends() system.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.services.brand_detector import BrandDetector
from app.services.entity_extractor import EntityExtractor
from app.services.intent_recognizer import IntentRecognizer

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _intent_recognizer_singleton() -> IntentRecognizer:
    """Build and initialise the IntentRecognizer exactly once per process."""
    recognizer = IntentRecognizer()
    recognizer.initialize()
    return recognizer


@lru_cache(maxsize=1)
def _entity_extractor_singleton() -> EntityExtractor:
    """Build and initialise the EntityExtractor exactly once per process."""
    extractor = EntityExtractor()
    extractor.initialize()
    return extractor


@lru_cache(maxsize=1)
def _brand_detector_singleton() -> BrandDetector:
    """Build and initialise the BrandDetector exactly once per process."""
    detector = BrandDetector()
    detector.initialize()
    return detector


# ---------------------------------------------------------------------------
# FastAPI Depends()-compatible providers
# ---------------------------------------------------------------------------


def get_intent_recognizer() -> IntentRecognizer:
    """
    Dependency provider for IntentRecognizer.

    Usage::

        @router.post("/intent/recognize")
        async def recognize(
            req: IntentRecognizeRequest,
            recognizer: IntentRecognizer = Depends(get_intent_recognizer),
        ):
            ...
    """
    return _intent_recognizer_singleton()


def get_entity_extractor() -> EntityExtractor:
    """
    Dependency provider for EntityExtractor.

    Usage::

        @router.post("/entity/extract")
        async def extract(
            req: EntityExtractRequest,
            extractor: EntityExtractor = Depends(get_entity_extractor),
        ):
            ...
    """
    return _entity_extractor_singleton()


def get_brand_detector() -> BrandDetector:
    """
    Dependency provider for BrandDetector.

    Usage::

        @router.post("/brand/detect")
        async def detect(
            req: BrandDetectRequest,
            detector: BrandDetector = Depends(get_brand_detector),
        ):
            ...
    """
    return _brand_detector_singleton()
