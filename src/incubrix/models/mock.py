from __future__ import annotations
import logging
from typing import List
from incubrix.models.base import BaseTranslator
from incubrix.core.schema import SupportedLanguage

logger = logging.getLogger(__name__)


class MockTranslator(BaseTranslator):
    """
    Deterministic mock translator for testing, rapid verification,
    and fallback validation without downloading weights.
    Appends language-specific prefixes and translates mock words while
    leaving __ENT_...__ tokens intact.
    """

    MOCK_LEXICON = {
        "hi": {"Hello": "नमस्ते", "world": "दुनिया", "welcome": "स्वागत", "creator": "क्रिएटर"},
        "ta": {"Hello": "வணக்கம்", "world": "உலகம்", "welcome": "வரவேற்பு", "creator": "படைப்பாளர்"},
        "te": {"Hello": "నమస్కారం", "world": "ప్రపంచం", "welcome": "స్వాగతం", "creator": "సృష్టికర్త"},
        "bn": {"Hello": "হ্যালো", "world": "বিশ্ব", "welcome": "স্বাগতম", "creator": "স্রষ্টা"},
        "mr": {"Hello": "नमस्कार", "world": "जग", "welcome": "स्वागत", "creator": "निर्माता"},
        "es": {"Hello": "Hola", "world": "mundo", "welcome": "bienvenido", "creator": "creador"},
        "fr": {"Hello": "Bonjour", "world": "monde", "welcome": "bienvenue", "creator": "créateur"},
        "de": {"Hello": "Hallo", "world": "Welt", "welcome": "willkommen", "creator": "Schöpfer"},
        "pt": {"Hello": "Olá", "world": "mundo", "welcome": "bem-vindo", "creator": "criador"},
        "id": {"Hello": "Halo", "world": "dunia", "welcome": "selamat datang", "creator": "pencipta"},
    }

    def __init__(self, model_id: str = "mock-translator", model_family: str = "Mock"):
        super().__init__(model_id=model_id, model_family=model_family)

    def load(self) -> None:
        self.is_loaded = True

    def supports_direction(self, source_lang: str, target_lang: str) -> bool:
        try:
            SupportedLanguage.from_str(source_lang)
            SupportedLanguage.from_str(target_lang)
            return True
        except ValueError:
            return False

    def translate(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        max_length: int = 512,
        num_beams: int = 1,
    ) -> List[str]:
        tgt_val = SupportedLanguage.from_str(target_lang).value
        results = []
        lexicon = self.MOCK_LEXICON.get(tgt_val, {})

        for text in texts:
            words = text.split(" ")
            translated_words = []
            for w in words:
                clean_w = w.strip(".,!?")
                if clean_w in lexicon:
                    translated_words.append(w.replace(clean_w, lexicon[clean_w]))
                else:
                    translated_words.append(w)
            results.append(" ".join(translated_words))
        return results
