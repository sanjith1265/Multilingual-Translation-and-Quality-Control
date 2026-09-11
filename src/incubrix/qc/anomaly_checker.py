from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from incubrix.core.schema import QCCheckDetail


class AnomalyValidator:
    """
    Deterministic Entity, Number, and Anomaly Validator (QC Check 3).
    Verifies that all protected numbers, entities, URLs, and hashtags were preserved,
    and detects degenerate failure modes like empty outputs, repetition loops,
    length explosions, or unresolved placeholders.
    """

    @staticmethod
    def _detect_repetition(text: str) -> bool:
        """Detect degenerate repetition loops across any script (Latin, Devanagari, Tamil, etc.)."""
        words = text.strip().split()
        if len(words) < 4:
            return False

        # 1. Single word repeated 3+ times consecutively
        for i in range(len(words) - 2):
            if words[i] == words[i + 1] == words[i + 2]:
                return True

        # 2. 2-gram phrase repeated 3+ times consecutively
        for i in range(len(words) - 5):
            p1 = (words[i], words[i + 1])
            p2 = (words[i + 2], words[i + 3])
            p3 = (words[i + 4], words[i + 5])
            if p1 == p2 == p3:
                return True

        # 3. 3-gram phrase repeated 2+ times consecutively
        for i in range(len(words) - 5):
            p1 = (words[i], words[i + 1], words[i + 2])
            p2 = (words[i + 3], words[i + 4], words[i + 5])
            if p1 == p2:
                return True

        return False

    def check(
        self,
        source_text: str,
        translated_text: str,
        expected_entities: Optional[List[str]] = None,
        threshold: float = 0.80,
    ) -> QCCheckDetail:
        flags: List[str] = []
        expected_entities = expected_entities or []

        # 1. Check for empty or whitespace output
        if not translated_text or not translated_text.strip():
            flags.append("EMPTY_OUTPUT")
            return QCCheckDetail(
                check_name="entity_and_anomaly_validation",
                passed=False,
                score=0.0,
                threshold=threshold,
                is_independent=True,
                details={"flags": flags, "error": "Translated output is empty"},
            )

        # 2. Check for unresolved sentinel placeholders
        unresolved = re.findall(r"_{1,3}ENT_\d+_{1,3}", translated_text)
        if unresolved:
            flags.append("UNRESOLVED_PLACEHOLDER")

        # 3. Check for repetitive generation loops
        if self._detect_repetition(translated_text):
            flags.append("REPETITIVE_LOOP")

        # 4. Check length ratio anomaly
        src_len = max(1, len(source_text.strip()))
        tgt_len = len(translated_text.strip())
        ratio = tgt_len / src_len
        if ratio > 3.5 and src_len > 15:
            flags.append("LENGTH_EXPLOSION")
        elif ratio < 0.2 and src_len > 25:
            flags.append("LENGTH_COLLAPSE")

        # 5. Check entity & number preservation
        preserved_count = 0
        missing_entities = []
        for ent in expected_entities:
            # Check presence of entity (case-insensitive for text, exact for numbers/symbols)
            if re.search(re.escape(ent), translated_text, re.IGNORECASE):
                preserved_count += 1
            else:
                missing_entities.append(ent)

        total_entities = len(expected_entities)
        entity_score = (preserved_count / total_entities) if total_entities > 0 else 1.0

        if missing_entities:
            flags.append(f"MISSING_ENTITIES:{len(missing_entities)}")

        # Aggregate score
        penalty = len(flags) * 0.25
        final_score = max(0.0, min(1.0, entity_score - penalty))
        passed = final_score >= threshold and "EMPTY_OUTPUT" not in flags and "REPETITIVE_LOOP" not in flags

        return QCCheckDetail(
            check_name="entity_and_anomaly_validation",
            passed=passed,
            score=round(final_score, 3),
            threshold=threshold,
            is_independent=True,
            details={
                "flags": flags,
                "length_ratio": round(ratio, 2),
                "entity_score": round(entity_score, 3),
                "missing_entities": missing_entities,
                "unresolved_placeholders": unresolved,
            },
        )
