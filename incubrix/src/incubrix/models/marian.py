from __future__ import annotations
import logging
import torch
from typing import List, Dict, Optional
from incubrix.models.base import BaseTranslator
from incubrix.core.schema import SupportedLanguage

logger = logging.getLogger(__name__)


class MarianTranslator(BaseTranslator):
    """
    Helsinki-NLP MarianMT translation backend.
    Represents an independent model family from NLLB.
    Used for comparative routing and independent back-translation QC.
    """

    # Mapping of supported pair checkpoints
    MODEL_CHECKPOINTS: Dict[str, str] = {
        # Romance / Germanic language pairs
        "en-es": "Helsinki-NLP/opus-mt-en-es",
        "es-en": "Helsinki-NLP/opus-mt-es-en",
        "en-fr": "Helsinki-NLP/opus-mt-en-fr",
        "fr-en": "Helsinki-NLP/opus-mt-fr-en",
        "en-de": "Helsinki-NLP/opus-mt-en-de",
        "de-en": "Helsinki-NLP/opus-mt-de-en",
        "en-pt": "Helsinki-NLP/opus-mt-tc-big-en-pt",
        "pt-en": "Helsinki-NLP/opus-mt-tc-big-pt-en",
        "en-id": "Helsinki-NLP/opus-mt-en-id",
        "id-en": "Helsinki-NLP/opus-mt-id-en",
        # Multilingual back-to-English fallback model
        "mul-en": "Helsinki-NLP/opus-mt-mul-en",
    }

    def __init__(self, device: str = "cpu"):
        super().__init__(model_id="Helsinki-NLP/MarianMT", model_family="MarianMT")
        self.device = device
        self._loaded_pairs: Dict[str, Any] = {}

    def get_checkpoint_for_pair(self, source_lang: str, target_lang: str) -> Optional[str]:
        pair_key = f"{source_lang}-{target_lang}"
        if pair_key in self.MODEL_CHECKPOINTS:
            return self.MODEL_CHECKPOINTS[pair_key]
        if target_lang == "en":
            return self.MODEL_CHECKPOINTS.get("mul-en")
        return None

    def supports_direction(self, source_lang: str, target_lang: str) -> bool:
        src = SupportedLanguage.from_str(source_lang).value
        tgt = SupportedLanguage.from_str(target_lang).value
        return self.get_checkpoint_for_pair(src, tgt) is not None

    def load_pair(self, checkpoint: str):
        if checkpoint in self._loaded_pairs:
            return self._loaded_pairs[checkpoint]

        logger.info(f"Loading MarianMT checkpoint: {checkpoint} on {self.device}...")
        from transformers import MarianMTModel, MarianTokenizer

        tokenizer = MarianTokenizer.from_pretrained(checkpoint)
        model = MarianMTModel.from_pretrained(checkpoint).to(self.device)
        model.eval()

        self._loaded_pairs[checkpoint] = (tokenizer, model)
        self.is_loaded = True
        return tokenizer, model

    def load(self) -> None:
        # On-demand loading for specific language pairs
        self.is_loaded = True

    def translate(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        max_length: int = 512,
        num_beams: int = 1,
    ) -> List[str]:
        if not texts:
            return []

        src = SupportedLanguage.from_str(source_lang).value
        tgt = SupportedLanguage.from_str(target_lang).value

        checkpoint = self.get_checkpoint_for_pair(src, tgt)
        if not checkpoint:
            raise ValueError(f"MarianMT does not support direction {src} -> {tgt}")

        tokenizer, model = self.load_pair(checkpoint)

        inputs = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        ).to(self.device)

        with torch.inference_mode():
            generated_tokens = model.generate(
                **inputs,
                max_new_tokens=max_length,
                num_beams=num_beams,
            )

        decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        return [t.strip() for t in decoded]

    def unload(self) -> None:
        self._loaded_pairs.clear()
        self.is_loaded = False
        import gc
        gc.collect()
        logger.info("MarianMT models unloaded from RAM.")
