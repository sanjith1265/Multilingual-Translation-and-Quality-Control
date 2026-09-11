from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SupportedLanguage(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    BENGALI = "bn"
    MARATHI = "mr"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    PORTUGUESE = "pt"
    INDONESIAN = "id"

    @classmethod
    def from_str(cls, lang: str) -> "SupportedLanguage":
        clean = lang.lower().strip()
        # Direct ISO 639-1 match
        for item in cls:
            if item.value == clean or item.name.lower() == clean:
                return item
        # Common aliases & NLLB codes
        mapping = {
            "eng": cls.ENGLISH, "eng_latn": cls.ENGLISH, "english": cls.ENGLISH,
            "hin": cls.HINDI, "hin_deva": cls.HINDI, "hindi": cls.HINDI,
            "tam": cls.TAMIL, "tam_taml": cls.TAMIL, "tamil": cls.TAMIL,
            "tel": cls.TELUGU, "tel_telu": cls.TELUGU, "telugu": cls.TELUGU,
            "ben": cls.BENGALI, "ben_beng": cls.BENGALI, "bengali": cls.BENGALI, "bangla": cls.BENGALI,
            "mar": cls.MARATHI, "mar_deva": cls.MARATHI, "marathi": cls.MARATHI,
            "spa": cls.SPANISH, "spa_latn": cls.SPANISH, "spanish": cls.SPANISH, "castilian": cls.SPANISH,
            "fra": cls.FRENCH, "fra_latn": cls.FRENCH, "french": cls.FRENCH,
            "deu": cls.GERMAN, "deu_latn": cls.GERMAN, "ger": cls.GERMAN, "german": cls.GERMAN,
            "por": cls.PORTUGUESE, "por_latn": cls.PORTUGUESE, "portuguese": cls.PORTUGUESE,
            "ind": cls.INDONESIAN, "ind_latn": cls.INDONESIAN, "indonesian": cls.INDONESIAN, "bahasa": cls.INDONESIAN,
        }
        if clean in mapping:
            return mapping[clean]
        raise ValueError(f"Language '{lang}' is not supported. Supported: {[e.value for e in cls]}")

    @property
    def nllb_code(self) -> str:
        """Map ISO code to NLLB-200 FLORES code."""
        nllb_map = {
            SupportedLanguage.ENGLISH: "eng_Latn",
            SupportedLanguage.HINDI: "hin_Deva",
            SupportedLanguage.TAMIL: "tam_Taml",
            SupportedLanguage.TELUGU: "tel_Telu",
            SupportedLanguage.BENGALI: "ben_Beng",
            SupportedLanguage.MARATHI: "mar_Deva",
            SupportedLanguage.SPANISH: "spa_Latn",
            SupportedLanguage.FRENCH: "fra_Latn",
            SupportedLanguage.GERMAN: "deu_Latn",
            SupportedLanguage.PORTUGUESE: "por_Latn",
            SupportedLanguage.INDONESIAN: "ind_Latn",
        }
        return nllb_map[self]


class TranslationSegment(BaseModel):
    id: str = Field(..., description="Unique segment identifier (preserved through pipeline)")
    text: str = Field(..., description="Input text for this segment")
    context: Optional[str] = Field(None, description="Optional creator context or scene tag")


class TranslationRequest(BaseModel):
    source_text: Optional[str] = Field(None, description="Single text input (shorthand)")
    segments: Optional[List[TranslationSegment]] = Field(None, description="List of segmented inputs")
    source_lang: str = Field(default="en", description="Source language code (e.g. 'en', 'hi', 'spa')")
    target_lang: str = Field(..., description="Target language code (e.g. 'hi', 'ta', 'es')")
    glossary: Dict[str, str] = Field(default_factory=dict, description="Pre-defined terminology translations")
    do_not_translate: List[str] = Field(default_factory=list, description="Terms that must remain unmodified")
    route_override: Optional[str] = Field(None, description="Optional model route override ('nllb', 'marian')")
    enable_qc: bool = Field(default=True, description="Whether to execute independent quality checks")


class RouteMetadata(BaseModel):
    model_name: str = Field(..., description="Selected model identifier")
    model_family: str = Field(..., description="Model family (e.g., 'NLLB', 'MarianMT')")
    device: str = Field(default="cpu", description="Execution device")
    quantization: str = Field(default="int8", description="Quantization mode")
    fallback_used: bool = Field(default=False, description="True if a fallback route was executed")
    latency_ms: float = Field(default=0.0, description="Inference runtime in milliseconds")
    peak_ram_mb: float = Field(default=0.0, description="Peak memory observed during inference")


class QCCheckDetail(BaseModel):
    check_name: str = Field(..., description="QC check identifier (e.g., 'lang_id', 'back_translation', 'entity_preservation')")
    passed: bool = Field(..., description="Whether this specific check passed its acceptance threshold")
    score: float = Field(..., description="Normalized score [0.0 - 1.0]")
    threshold: float = Field(..., description="Threshold required for pass")
    is_independent: bool = Field(..., description="Whether the check uses an independent model/mechanism")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed diagnostic metrics")


class QCResult(BaseModel):
    passed: bool = Field(..., description="Overall pass status (all critical checks passed)")
    overall_confidence: float = Field(..., description="Aggregate confidence score [0.0 - 1.0]")
    checks: List[QCCheckDetail] = Field(default_factory=list, description="Individual QC check breakdowns")
    flags: List[str] = Field(default_factory=list, description="List of warning/failure flags")
    requires_human_review: bool = Field(default=False, description="True if sent to review queue")


class TranslationOutput(BaseModel):
    id: str = Field(..., description="Preserved segment ID")
    source_text: str = Field(..., description="Original input text")
    translated_text: str = Field(..., description="Final translated text")
    source_lang: str
    target_lang: str
    route_metadata: RouteMetadata
    qc_result: Optional[QCResult] = None
    preserved_entities: List[str] = Field(default_factory=list, description="Preserved names, numbers, URLs, hashtags")
    review_status: str = Field(default="APPROVED", description="APPROVED, FLAGGED, or REJECTED")
    runtime_ms: float = Field(default=0.0, description="End-to-end processing latency")
    warnings: List[str] = Field(default_factory=list)


class BatchTranslationRequest(BaseModel):
    batch_id: Optional[str] = None
    segments: List[TranslationSegment]
    source_lang: str = "en"
    target_lang: str
    glossary: Dict[str, str] = Field(default_factory=dict)
    do_not_translate: List[str] = Field(default_factory=list)
    route_override: Optional[str] = None
    enable_qc: bool = True
    enable_cache: bool = True


class BatchTranslationResponse(BaseModel):
    batch_id: str
    total_segments: int
    completed_segments: int
    failed_segments: int
    cached_hits: int
    outputs: List[TranslationOutput]
    total_runtime_ms: float
    review_queue_count: int


class ReviewQueueItem(BaseModel):
    review_id: str
    segment_id: str
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    model_used: str
    qc_flags: List[str]
    suggested_action: str
    created_at: str
