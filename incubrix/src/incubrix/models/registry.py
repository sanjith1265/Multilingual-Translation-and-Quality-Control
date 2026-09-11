from __future__ import annotations
import logging
from typing import Dict, Optional, Type
from incubrix.models.base import BaseTranslator
from incubrix.models.nllb import NLLBTranslator
from incubrix.models.marian import MarianTranslator
from incubrix.models.mock import MockTranslator

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Central registry and lifecycle manager for translation backends.
    Caches model instances and manages CPU memory pressure.
    """

    def __init__(self):
        self._instances: Dict[str, BaseTranslator] = {}

    def get_translator(self, route: str = "nllb", **kwargs) -> BaseTranslator:
        key = route.lower()
        if key in self._instances:
            return self._instances[key]

        if key in ("nllb", "nllb-200", "facebook/nllb-200-distilled-600m"):
            instance = NLLBTranslator(**kwargs)
        elif key in ("marian", "marianmt", "helsinki"):
            instance = MarianTranslator(**kwargs)
        elif key in ("mock", "mock-translator", "test"):
            instance = MockTranslator(**kwargs)
        else:
            raise ValueError(f"Unknown translation backend route: '{route}'. Available: ['nllb', 'marian', 'mock']")

        self._instances[key] = instance
        return instance

    def unload_all(self):
        for name, inst in self._instances.items():
            inst.unload()
        self._instances.clear()
