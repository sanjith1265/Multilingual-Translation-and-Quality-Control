from __future__ import annotations
import logging
import torch
from typing import List, Optional
from incubrix.models.base import BaseTranslator
from incubrix.core.schema import SupportedLanguage

logger = logging.getLogger(__name__)


class NLLBTranslator(BaseTranslator):
    """
    NLLB-200 Distilled 600M Translator backend.
    Supports direct multi-directional translation across all 10 target languages
    plus English on CPU, with optional dynamic int8 quantization.
    """

    MODEL_CHECKPOINT = "facebook/nllb-200-distilled-600M"

    def __init__(
        self,
        checkpoint: str = MODEL_CHECKPOINT,
        device: str = "cpu",
        quantize_int8: bool = True,
    ):
        super().__init__(model_id=checkpoint, model_family="NLLB")
        self.checkpoint = checkpoint
        self.device = device
        self.quantize_int8 = quantize_int8
        self.tokenizer = None
        self.model = None

    def load(self) -> None:
        if self.is_loaded:
            return

        logger.info(f"Loading NLLB model: {self.checkpoint} on {self.device}...")
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        self.tokenizer = AutoTokenizer.from_pretrained(self.checkpoint)
        model = AutoModelForSeq2SeqLM.from_pretrained(
            self.checkpoint,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
        )

        if self.quantize_int8 and self.device == "cpu":
            logger.info("Applying dynamic int8 quantization for CPU...")
            try:
                model = torch.ao.quantization.quantize_dynamic(
                    model, {torch.nn.Linear}, dtype=torch.qint8
                )
            except Exception as e:
                logger.warning(f"Dynamic quantization failed, falling back to float32: {e}")

        model.to(self.device)
        model.eval()
        self.model = model
        self.is_loaded = True
        logger.info("NLLB model successfully loaded into memory.")

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
        if not texts:
            return []

        src_enum = SupportedLanguage.from_str(source_lang)
        tgt_enum = SupportedLanguage.from_str(target_lang)

        if not self.is_loaded:
            self.load()

        src_flores = src_enum.nllb_code
        tgt_flores = tgt_enum.nllb_code

        self.tokenizer.src_lang = src_flores
        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        ).to(self.device)

        forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt_flores)

        with torch.inference_mode():
            generated_tokens = self.model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_new_tokens=max_length,
                num_beams=num_beams,
                early_stopping=True,
            )

        decoded = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        return [t.strip() for t in decoded]

    def unload(self) -> None:
        if self.is_loaded:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            self.is_loaded = False
            import gc
            gc.collect()
            logger.info("NLLB model unloaded from RAM.")
