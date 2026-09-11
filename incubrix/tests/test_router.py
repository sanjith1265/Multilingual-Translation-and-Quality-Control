from __future__ import annotations
import pytest
from incubrix.routing.router import TranslationRouter


def test_router_indic_pairs():
    router = TranslationRouter()
    decision = router.route("en", "hi")
    assert decision.primary_route == "nllb"
    assert "Indic" in decision.reason

    decision_tamil = router.route("en", "ta")
    assert decision_tamil.primary_route == "nllb"


def test_router_european_pairs():
    router = TranslationRouter()
    decision_speed = router.route("en", "es", preference="speed")
    assert decision_speed.primary_route == "marian"

    decision_de = router.route("en", "de", preference="memory")
    assert decision_de.primary_route == "marian"


def test_router_override():
    router = TranslationRouter()
    decision = router.route("en", "es", override="mock")
    assert decision.primary_route == "mock"


def test_router_fallback():
    router = TranslationRouter()
    # Mocking execution with fallback
    outputs, meta = router.execute_with_fallback(
        texts=["Hello"],
        source_lang="en",
        target_lang="es",
        override_route="mock",
    )
    assert len(outputs) == 1
    assert meta.model_family == "Mock"
