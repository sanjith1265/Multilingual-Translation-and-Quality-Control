from __future__ import annotations
import logging
from typing import List, Optional, Dict, Any
from incubrix.core.schema import QCResult, QCCheckDetail
from incubrix.qc.lang_id import LanguageIdentifier
from incubrix.qc.back_translator import BackTranslationValidator
from incubrix.qc.anomaly_checker import AnomalyValidator
from incubrix.qc.review_queue import ReviewQueueManager

logger = logging.getLogger(__name__)


class QCEngine:
    """
    Automated Multi-Stage Quality Control Engine.
    Coordinates 3 independent checks:
      1. Language Identification (script and probabilistic detection)
      2. Independent Model Back-Translation (distinct model family)
      3. Deterministic Entity, Number & Anomaly Validation
    Enforces that production models never grade themselves.
    """

    def __init__(
        self,
        lang_identifier: Optional[LanguageIdentifier] = None,
        back_translator: Optional[BackTranslationValidator] = None,
        anomaly_validator: Optional[AnomalyValidator] = None,
        review_queue: Optional[ReviewQueueManager] = None,
        confidence_threshold: float = 0.65,
    ):
        self.lang_identifier = lang_identifier or LanguageIdentifier()
        self.back_translator = back_translator or BackTranslationValidator()
        self.anomaly_validator = anomaly_validator or AnomalyValidator()
        self.review_queue = review_queue or ReviewQueueManager()
        self.confidence_threshold = confidence_threshold

    def evaluate(
        self,
        segment_id: str,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        production_model_family: str,
        expected_entities: Optional[List[str]] = None,
        enable_back_translation: bool = True,
    ) -> QCResult:
        """
        Run the complete QC battery on a translation segment.
        """
        checks: List[QCCheckDetail] = []
        all_flags: List[str] = []

        # Check 1: Language Identification (Independent)
        c1 = self.lang_identifier.check(translated_text, target_lang)
        checks.append(c1)
        if not c1.passed:
            all_flags.append(f"WRONG_LANGUAGE (detected: {c1.details.get('detected_lang', 'unknown')})")

        # Check 2: Independent Back-Translation (Independent model family)
        if enable_back_translation:
            c2 = self.back_translator.check(
                original_source=source_text,
                translated_text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
                production_model_family=production_model_family,
            )
            checks.append(c2)
            if not c2.passed:
                all_flags.append(f"SEMANTIC_DRIFT (similarity: {c2.score})")
        else:
            c2 = QCCheckDetail(
                check_name="independent_back_translation",
                passed=True,
                score=1.0,
                threshold=0.35,
                is_independent=True,
                details={"status": "skipped_by_config"},
            )
            checks.append(c2)

        # Check 3: Deterministic Entity & Anomaly Validation (Deterministic/Independent)
        c3 = self.anomaly_validator.check(
            source_text=source_text,
            translated_text=translated_text,
            expected_entities=expected_entities,
        )
        checks.append(c3)
        if not c3.passed:
            all_flags.extend(c3.details.get("flags", []))

        # Weighting:
        # LangID: 0.35, BackTrans: 0.35, Anomaly/Entity: 0.30
        overall_confidence = (0.35 * c1.score) + (0.35 * c2.score) + (0.30 * c3.score)
        overall_confidence = round(max(0.0, min(1.0, overall_confidence)), 3)

        passed = (
            c1.passed
            and c3.passed
            and overall_confidence >= self.confidence_threshold
            and not any("EMPTY_OUTPUT" in f or "REPETITIVE_LOOP" in f for f in all_flags)
        )

        requires_human_review = not passed

        qc_result = QCResult(
            passed=passed,
            overall_confidence=overall_confidence,
            checks=checks,
            flags=all_flags,
            requires_human_review=requires_human_review,
        )

        # If flagged, automatically append to review_queue.json
        if requires_human_review:
            self.review_queue.add_item(
                segment_id=segment_id,
                source_text=source_text,
                translated_text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
                model_used=production_model_family,
                qc_flags=all_flags,
                suggested_action=f"Review flagged segment. Confidence: {overall_confidence}. Flags: {', '.join(all_flags)}",
            )

        return qc_result
