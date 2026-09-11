from __future__ import annotations
import abc
import os
import psutil
from typing import List, Optional


class BaseTranslator(abc.ABC):
    """Abstract base class for all neural translation backends."""

    def __init__(self, model_id: str, model_family: str):
        self.model_id = model_id
        self.model_family = model_family
        self.is_loaded = False
        self._process = psutil.Process(os.getpid())

    @abc.abstractmethod
    def load(self) -> None:
        """Load model weights and tokenizer into memory."""
        pass

    @abc.abstractmethod
    def translate(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        max_length: int = 512,
        num_beams: int = 1,
    ) -> List[str]:
        """Translate a batch of strings from source_lang to target_lang."""
        pass

    @abc.abstractmethod
    def supports_direction(self, source_lang: str, target_lang: str) -> bool:
        """Check if model supports translation between the given language pair."""
        pass

    def get_memory_usage_mb(self) -> float:
        """Return current RSS memory consumption in Megabytes."""
        return self._process.memory_info().rss / (1024 * 1024)

    def unload(self) -> None:
        """Unload model from RAM if needed to manage memory limits."""
        pass
