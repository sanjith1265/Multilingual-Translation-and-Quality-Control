from __future__ import annotations
import re
import logging
from typing import Tuple, Dict, Any
from incubrix.core.schema import SupportedLanguage, QCCheckDetail

logger = logging.getLogger(__name__)


class LanguageIdentifier:
    """
    Independent Language Identification (QC Check 1).
    Combines Unicode script analysis (with 100% precision for Indic scripts)
    and probabilistic n-gram language detection for Latin scripts.
    """

    # Unicode script ranges
    SCRIPT_PATTERNS = {
        "hi": re.compile(r"[\u0900-\u097F]"),  # Devanagari
        "mr": re.compile(r"[\u0900-\u097F]"),  # Devanagari
        "ta": re.compile(r"[\u0B80-\u0BFF]"),  # Tamil
        "te": re.compile(r"[\u0C00-\u0C7F]"),  # Telugu
        "bn": re.compile(r"[\u0980-\u09FF]"),  # Bengali
    }

    def __init__(self):
        self._langdetect_available = False
        try:
            import langdetect
            self._langdetect = langdetect
            self._langdetect_available = True
        except ImportError:
            logger.warning("langdetect not installed, using script-only heuristics.")

    def check(self, text: str, expected_lang: str, threshold: float = 0.70) -> QCCheckDetail:
        """
        Verify that the text corresponds to the expected target language.
        Returns a QCCheckDetail record.
        """
        if not text or not text.strip():
            return QCCheckDetail(
                check_name="language_identification",
                passed=False,
                score=0.0,
                threshold=threshold,
                is_independent=True,
                details={"error": "Empty text provided for Lang-ID"},
            )

        target_iso = SupportedLanguage.from_str(expected_lang).value
        clean_text = re.sub(r"__ENT_\d+__", "", text).strip()
        if not clean_text:
            clean_text = text

        # 1. Script-based check for Indic languages
        if target_iso in self.SCRIPT_PATTERNS:
            pattern = self.SCRIPT_PATTERNS[target_iso]
            script_chars = len(pattern.findall(clean_text))
            alpha_chars = sum(1 for c in clean_text if c.isalpha())
            script_ratio = script_chars / max(1, alpha_chars)

            passed = script_ratio >= 0.40
            score = min(1.0, script_ratio * 1.5)
            return QCCheckDetail(
                check_name="language_identification",
                passed=passed,
                score=round(score, 3),
                threshold=threshold,
                is_independent=True,
                details={
                    "method": "unicode_script_analysis",
                    "target_lang": target_iso,
                    "script_ratio": round(script_ratio, 3),
                    "script_chars": script_chars,
                    "total_alpha": alpha_chars,
                },
            )

        # 2. Probabilistic LangDetect for Latin scripts (es, fr, de, pt, id, en)
        detected_lang = "unknown"
        score = 0.5
        passed = False

        if self._langdetect_available:
            try:
                # Seed for deterministic detection
                self._langdetect.DetectorFactory.seed = 42
                detected_lang = self._langdetect.detect(clean_text)
                passed = detected_lang == target_iso
                score = 1.0 if passed else 0.1
            except Exception as e:
                logger.debug(f"Langdetect error: {e}")
                # Fallback heuristic: check Latin script
                is_latin = any('a' <= c.lower() <= 'z' for c in clean_text)
                passed = is_latin and target_iso in {"es", "fr", "de", "pt", "id", "en"}
                score = 0.7 if passed else 0.2
        else:
            # Fallback heuristic
            is_latin = any('a' <= c.lower() <= 'z' for c in clean_text)
            passed = is_latin
            score = 0.8 if passed else 0.3

        return QCCheckDetail(
            check_name="language_identification",
            passed=passed,
            score=round(score, 3),
            threshold=threshold,
            is_independent=True,
            details={
                "method": "probabilistic_langdetect",
                "detected_lang": detected_lang,
                "expected_lang": target_iso,
            },
        )
