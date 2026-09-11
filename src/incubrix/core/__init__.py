"""
Core module containing data schemas, entity masking, and persistent cache.
"""
from incubrix.core.schema import (
    TranslationSegment,
    TranslationRequest,
    TranslationOutput,
    BatchTranslationRequest,
    BatchTranslationResponse,
    QCResult,
    QCCheckDetail,
    RouteMetadata,
    ReviewQueueItem,
    SupportedLanguage,
)
from incubrix.core.entity_masker import EntityMasker, MaskResult
from incubrix.core.cache import TranslationCache

__all__ = [
    "TranslationSegment",
    "TranslationRequest",
    "TranslationOutput",
    "BatchTranslationRequest",
    "BatchTranslationResponse",
    "QCResult",
    "QCCheckDetail",
    "RouteMetadata",
    "ReviewQueueItem",
    "SupportedLanguage",
    "EntityMasker",
    "MaskResult",
    "TranslationCache",
]
