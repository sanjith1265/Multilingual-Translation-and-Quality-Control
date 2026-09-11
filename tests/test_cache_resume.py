from __future__ import annotations
import os
import pytest
from pathlib import Path
from incubrix.core.cache import TranslationCache
from incubrix.core.schema import TranslationSegment, BatchTranslationRequest
from incubrix.pipeline import TranslationPipeline


def test_cache_set_and_get(tmp_path):
    db_file = tmp_path / "test_cache.db"
    cache = TranslationCache(db_path=str(db_file))

    src_text = "Hello world"
    data = {"translated_text": "Hola mundo", "model": "mock"}

    assert cache.get_segment(src_text, "en", "es", "mock") is None

    cache.set_segment(src_text, "en", "es", "mock", data)
    cached = cache.get_segment(src_text, "en", "es", "mock")

    assert cached is not None
    assert cached["translated_text"] == "Hola mundo"


def test_batch_checkpoint_and_resume(tmp_path):
    db_file = tmp_path / "test_resume.db"
    cache = TranslationCache(db_path=str(db_file))
    pipeline = TranslationPipeline(cache=cache)

    batch_id = "test-resume-batch-001"
    segments = [
        TranslationSegment(id="seg-1", text="Segment one text"),
        TranslationSegment(id="seg-2", text="Segment two text"),
        TranslationSegment(id="seg-3", text="Segment three text"),
    ]

    # Pre-populate segment 1 and 2 as completed in a prior interrupted run
    cache.record_batch_checkpoint(
        batch_id, "seg-1",
        {"id": "seg-1", "source_text": "Segment one text", "translated_text": "Seg 1 Trans", "source_lang": "en", "target_lang": "es", "route_metadata": {"model_name": "mock", "model_family": "Mock", "device": "cpu", "quantization": "int8", "fallback_used": False, "latency_ms": 1.0, "peak_ram_mb": 10.0}, "preserved_entities": [], "review_status": "APPROVED", "runtime_ms": 1.0, "warnings": []}
    )
    cache.record_batch_checkpoint(
        batch_id, "seg-2",
        {"id": "seg-2", "source_text": "Segment two text", "translated_text": "Seg 2 Trans", "source_lang": "en", "target_lang": "es", "route_metadata": {"model_name": "mock", "model_family": "Mock", "device": "cpu", "quantization": "int8", "fallback_used": False, "latency_ms": 1.0, "peak_ram_mb": 10.0}, "preserved_entities": [], "review_status": "APPROVED", "runtime_ms": 1.0, "warnings": []}
    )

    req = BatchTranslationRequest(
        batch_id=batch_id,
        segments=segments,
        source_lang="en",
        target_lang="es",
        enable_qc=False,
        enable_cache=True,
    )

    resp = pipeline.translate_batch(req)

    # Seg-1 and Seg-2 should be retrieved from checkpoint (cached hits = 2)
    assert resp.completed_segments == 3
    assert resp.cached_hits == 2
    assert resp.outputs[0].translated_text == "Seg 1 Trans"
    assert resp.outputs[1].translated_text == "Seg 2 Trans"
    # Seg-3 was translated on resume
    assert resp.outputs[2].id == "seg-3"
