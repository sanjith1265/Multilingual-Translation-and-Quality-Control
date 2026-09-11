from __future__ import annotations
import pytest
from incubrix.core.entity_masker import EntityMasker


def test_entity_masker_urls_and_hashtags():
    masker = EntityMasker()
    text = "Follow @creator and check out https://incubrix.com/demo with #trend2026!"
    
    masked = masker.mask(text)
    assert "__ENT_0__" in masked.masked_text
    assert "__ENT_1__" in masked.masked_text
    assert len(masked.items) >= 3

    # Simulated translation that retains placeholders
    simulated_translated = masked.masked_text.replace("Follow", "Siga").replace("and check out", "y mira")
    
    unmasked = masker.unmask(simulated_translated, masked)
    assert "@creator" in unmasked.unmasked_text
    assert "https://incubrix.com/demo" in unmasked.unmasked_text
    assert "#trend2026" in unmasked.unmasked_text
    assert unmasked.preservation_ratio == 1.0
    assert len(unmasked.missing_entities) == 0


def test_entity_masker_numbers_and_currencies():
    masker = EntityMasker()
    text = "Save $25,000 or ₹9,999 on 50% discount!"
    masked = masker.mask(text)
    
    unmasked = masker.unmask(masked.masked_text, masked)
    assert "$25,000" in unmasked.unmasked_text
    assert "₹9,999" in unmasked.unmasked_text
    assert "50%" in unmasked.unmasked_text
    assert unmasked.preservation_ratio == 1.0


def test_entity_masker_dnt_and_glossary():
    masker = EntityMasker()
    text = "Use IncuBrix AI for content repurposing."
    dnt = ["IncuBrix AI"]
    glossary = {"repurposing": "पुनर्उपयोग"}
    
    masked = masker.mask(text, do_not_translate=dnt, glossary=glossary)
    assert len(masked.items) >= 2
    
    unmasked = masker.unmask(masked.masked_text, masked)
    assert "IncuBrix AI" in unmasked.unmasked_text
    assert "पुनर्उपयोग" in unmasked.unmasked_text
    assert unmasked.preservation_ratio == 1.0


def test_entity_masker_missing_entity_warning():
    masker = EntityMasker()
    text = "Visit https://incubrix.com today."
    masked = masker.mask(text)
    
    # Simulate a translation that drops the placeholder
    corrupted_translated = "Visitez notre site web aujourd'hui."
    unmasked = masker.unmask(corrupted_translated, masked)
    
    assert unmasked.preservation_ratio == 0.0
    assert "https://incubrix.com" in unmasked.missing_entities
    assert len(unmasked.warnings) > 0
