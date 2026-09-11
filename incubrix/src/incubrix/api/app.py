from __future__ import annotations
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from incubrix.core.schema import (
    TranslationRequest,
    TranslationOutput,
    TranslationSegment,
    BatchTranslationRequest,
    BatchTranslationResponse,
    SupportedLanguage,
)
from incubrix.pipeline import TranslationPipeline
from incubrix.qc.review_queue import ReviewQueueManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("incubrix.api")

app = FastAPI(
    title="IncuBrix Translation & Independent QC API",
    description="Scalable, CPU-first open-source translation microservice with independent multi-stage quality control. (SASTRA 2027 Track 04)",
    version="1.0.0",
)

pipeline = TranslationPipeline()
review_mgr = ReviewQueueManager()


@app.get("/v1/health")
def health():
    import psutil
    import os
    proc = psutil.Process(os.getpid())
    return {
        "status": "healthy",
        "service": "incubrix-translation-qc",
        "ram_rss_mb": round(proc.memory_info().rss / (1024 * 1024), 2),
        "supported_languages": [lang.value for lang in SupportedLanguage],
    }


@app.get("/v1/languages")
def get_languages():
    return {
        "supported_languages": [
            {"code": lang.value, "name": lang.name.capitalize(), "nllb_code": lang.nllb_code}
            for lang in SupportedLanguage
        ]
    }


@app.post("/v1/translate", response_model=TranslationOutput)
def translate_single(req: TranslationRequest):
    text_to_translate = req.source_text
    segment_id = "single-001"
    if req.segments and len(req.segments) > 0:
        segment_id = req.segments[0].id
        text_to_translate = req.segments[0].text

    if not text_to_translate:
        raise HTTPException(status_code=400, detail="Missing source text or segments.")

    try:
        segment = TranslationSegment(id=segment_id, text=text_to_translate)
        out = pipeline.translate_segment(
            segment=segment,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            glossary=req.glossary,
            do_not_translate=req.do_not_translate,
            route_override=req.route_override,
            enable_qc=req.enable_qc,
        )
        return out
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Translation API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/batch", response_model=BatchTranslationResponse)
def translate_batch(req: BatchTranslationRequest):
    try:
        return pipeline.translate_batch(req)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Batch API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/review-queue")
def get_review_queue():
    items = review_mgr.get_all()
    return {"total_flagged": len(items), "items": items}


@app.delete("/v1/review-queue")
def clear_review_queue():
    review_mgr.clear()
    return {"status": "cleared"}
