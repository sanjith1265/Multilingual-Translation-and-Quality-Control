from __future__ import annotations
import time
import uuid
import logging
from typing import List, Dict, Optional, Tuple
from incubrix.core.schema import (
    TranslationSegment,
    TranslationRequest,
    TranslationOutput,
    BatchTranslationRequest,
    BatchTranslationResponse,
    RouteMetadata,
    QCResult,
    SupportedLanguage,
)
from incubrix.core.entity_masker import EntityMasker
from incubrix.core.cache import TranslationCache
from incubrix.routing.router import TranslationRouter
from incubrix.qc.engine import QCEngine

logger = logging.getLogger(__name__)


class TranslationPipeline:
    """
    Unified end-to-end translation pipeline.
    Orchestrates:
      1. Deterministic Entity, URL, Mention, Hashtag, Number & Glossary Masking
      2. Persistent SQLite Cache Lookup & Resume
      3. Dynamic Routing across open models (NLLB, MarianMT)
      4. Deterministic Entity Unmasking and Restoration Validation
      5. Automated Multi-Stage Independent Quality Control
      6. Review Queue Flagging
    """

    def __init__(
        self,
        router: Optional[TranslationRouter] = None,
        qc_engine: Optional[QCEngine] = None,
        cache: Optional[TranslationCache] = None,
        masker: Optional[EntityMasker] = None,
    ):
        self.router = router or TranslationRouter()
        self.qc_engine = qc_engine or QCEngine()
        self.cache = cache or TranslationCache()
        self.masker = masker or EntityMasker()

    def translate_segment(
        self,
        segment: TranslationSegment,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
        do_not_translate: Optional[List[str]] = None,
        route_override: Optional[str] = None,
        enable_qc: bool = True,
        enable_cache: bool = True,
    ) -> TranslationOutput:
        start_time = time.perf_counter()
        glossary = glossary or {}
        do_not_translate = do_not_translate or []

        # Validate languages
        SupportedLanguage.from_str(source_lang)
        SupportedLanguage.from_str(target_lang)

        # 1. Check cache
        cache_model_id = route_override or "default-router"
        if enable_cache:
            cached = self.cache.get_segment(segment.text, source_lang, target_lang, cache_model_id)
            if cached:
                cached["id"] = segment.id
                cached["runtime_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
                return TranslationOutput(**cached)

        # 2. Pre-processing: Mask entities, numbers, URLs, hashtags, DNT & glossary
        mask_res = self.masker.mask(
            segment.text,
            do_not_translate=do_not_translate,
            glossary=glossary,
        )

        # 3. Routing & Neural Inference
        t0 = time.perf_counter()
        raw_outputs, route_meta = self.router.execute_with_fallback(
            texts=[mask_res.masked_text],
            source_lang=source_lang,
            target_lang=target_lang,
            override_route=route_override,
        )
        inference_latency_ms = (time.perf_counter() - t0) * 1000
        route_meta.latency_ms = round(inference_latency_ms, 2)

        translated_masked = raw_outputs[0] if raw_outputs else ""

        # 4. Post-processing: Unmask and restore entities deterministically
        unmask_res = self.masker.unmask(translated_masked, mask_res)
        final_text = unmask_res.unmasked_text

        # 5. Independent Multi-Stage Quality Control
        qc_result = None
        review_status = "APPROVED"
        if enable_qc:
            expected_entities = [item.original_value for item in mask_res.items if item.category != "glossary"]
            qc_result = self.qc_engine.evaluate(
                segment_id=segment.id,
                source_text=segment.text,
                translated_text=final_text,
                source_lang=source_lang,
                target_lang=target_lang,
                production_model_family=route_meta.model_family,
                expected_entities=expected_entities,
            )
            if qc_result.requires_human_review:
                review_status = "FLAGGED"

        total_runtime_ms = round((time.perf_counter() - start_time) * 1000, 2)

        output = TranslationOutput(
            id=segment.id,
            source_text=segment.text,
            translated_text=final_text,
            source_lang=source_lang,
            target_lang=target_lang,
            route_metadata=route_meta,
            qc_result=qc_result,
            preserved_entities=unmask_res.preserved_entities,
            review_status=review_status,
            runtime_ms=total_runtime_ms,
            warnings=unmask_res.warnings,
        )

        # 6. Save to cache
        if enable_cache:
            self.cache.set_segment(
                segment.text, source_lang, target_lang, cache_model_id, output.model_dump()
            )

        return output

    def translate_batch(self, request: BatchTranslationRequest) -> BatchTranslationResponse:
        batch_id = request.batch_id or f"batch-{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()

        outputs: List[TranslationOutput] = []
        cached_hits = 0
        failed_count = 0
        review_count = 0

        # Check existing checkpoints for resume capability
        completed_checkpoints = {}
        if request.enable_cache:
            completed_checkpoints = self.cache.get_batch_completed_segments(batch_id)

        for segment in request.segments:
            # Check if segment was already processed in this batch
            if segment.id in completed_checkpoints:
                out = TranslationOutput(**completed_checkpoints[segment.id])
                outputs.append(out)
                cached_hits += 1
                if out.review_status == "FLAGGED":
                    review_count += 1
                continue

            try:
                out = self.translate_segment(
                    segment=segment,
                    source_lang=request.source_lang,
                    target_lang=request.target_lang,
                    glossary=request.glossary,
                    do_not_translate=request.do_not_translate,
                    route_override=request.route_override,
                    enable_qc=request.enable_qc,
                    enable_cache=request.enable_cache,
                )
                outputs.append(out)
                if out.review_status == "FLAGGED":
                    review_count += 1

                # Save checkpoint immediately for atomic resume
                if request.enable_cache:
                    self.cache.record_batch_checkpoint(batch_id, segment.id, out.model_dump())

            except Exception as e:
                logger.error(f"Failed processing segment {segment.id}: {e}")
                failed_count += 1

        total_runtime_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return BatchTranslationResponse(
            batch_id=batch_id,
            total_segments=len(request.segments),
            completed_segments=len(outputs),
            failed_segments=failed_count,
            cached_hits=cached_hits,
            outputs=outputs,
            total_runtime_ms=total_runtime_ms,
            review_queue_count=review_count,
        )
