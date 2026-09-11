from __future__ import annotations
import json
import pytest
from pathlib import Path
from incubrix.qc.engine import QCEngine


def test_fault_injection_suite_precision_recall():
    suite_file = Path("d:/incubrix/data/fault_injection_suite.json")
    with open(suite_file, "r", encoding="utf-8") as f:
        injections = json.load(f)["injections"]

    engine = QCEngine()
    tp, tn, fp, fn = 0, 0, 0, 0

    for item in injections:
        res = engine.evaluate(
            segment_id=item["id"],
            source_text=item["source_text"],
            translated_text=item["translated_text"],
            source_lang=item["source_lang"],
            target_lang=item["target_lang"],
            production_model_family="NLLB",
            expected_entities=item.get("expected_entities", []),
        )

        should_pass = item["should_pass"]
        actual_pass = res.passed

        if not should_pass and not actual_pass:
            tp += 1
        elif should_pass and actual_pass:
            tn += 1
        elif should_pass and not actual_pass:
            fp += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0

    # Ensure high recall (identifies injected faults) and high precision
    assert recall >= 0.85, f"Recall too low: {recall}"
    assert precision >= 0.80, f"Precision too low: {precision}"
