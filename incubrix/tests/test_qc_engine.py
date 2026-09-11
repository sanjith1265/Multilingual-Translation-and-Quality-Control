from __future__ import annotations
import pytest
from incubrix.qc.lang_id import LanguageIdentifier
from incubrix.qc.back_translator import BackTranslationValidator
from incubrix.qc.anomaly_checker import AnomalyValidator
from incubrix.qc.engine import QCEngine
from incubrix.qc.review_queue import ReviewQueueManager


def test_lang_id_indic_script():
    identifier = LanguageIdentifier()
    hindi_text = "यह एक हिंदी अनुवाद है।"
    res = identifier.check(hindi_text, "hi")
    assert res.passed is True
    assert res.score >= 0.7


def test_lang_id_wrong_script():
    identifier = LanguageIdentifier()
    # English text passed when Hindi was expected
    english_text = "This text remained completely in English."
    res = identifier.check(english_text, "hi")
    assert res.passed is False


def test_back_translator_similarity():
    sim = BackTranslationValidator.compute_lexical_similarity(
        "Welcome to the video",
        "Welcome to this video tutorial"
    )
    assert sim > 0.4


def test_anomaly_empty_output():
    validator = AnomalyValidator()
    res = validator.check("Source sentence", "")
    assert res.passed is False
    assert "EMPTY_OUTPUT" in res.details["flags"]


def test_anomaly_repetition_loop():
    validator = AnomalyValidator()
    repeated = "video edit video edit video edit video edit video edit"
    res = validator.check("Short sentence", repeated)
    assert res.passed is False
    assert "REPETITIVE_LOOP" in res.details["flags"]


def test_anomaly_missing_entities():
    validator = AnomalyValidator()
    res = validator.check(
        source_text="Visit https://incubrix.com and save 50%",
        translated_text="Sitio web sin enlaces",
        expected_entities=["https://incubrix.com", "50%"],
    )
    assert res.passed is False
    assert any("MISSING_ENTITIES" in f for f in res.details["flags"])


def test_qc_engine_flags_and_queues(tmp_path):
    q_file = tmp_path / "review_queue.json"
    queue_mgr = ReviewQueueManager(queue_file=str(q_file))
    engine = QCEngine(review_queue=queue_mgr)

    # Injected corrupted output
    res = engine.evaluate(
        segment_id="corrupt-01",
        source_text="Follow @channel",
        translated_text="",  # Empty
        source_lang="en",
        target_lang="hi",
        production_model_family="NLLB",
    )

    assert res.passed is False
    assert res.requires_human_review is True

    # Check that item was written to review queue
    items = queue_mgr.get_all()
    assert len(items) == 1
    assert items[0]["segment_id"] == "corrupt-01"
