from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


@dataclass
class MaskItem:
    placeholder: str
    original_value: str
    replacement_value: str
    category: str  # 'url', 'hashtag', 'mention', 'email', 'number', 'dnt', 'glossary'
    start_pos: int
    end_pos: int


@dataclass
class MaskResult:
    masked_text: str
    items: List[MaskItem] = field(default_factory=list)
    glossary_applied: Dict[str, str] = field(default_factory=dict)


@dataclass
class UnmaskResult:
    unmasked_text: str
    preserved_entities: List[str]
    missing_entities: List[str]
    preservation_ratio: float
    warnings: List[str]


class EntityMasker:
    """
    Deterministic entity masking and restoration engine.
    Protects URLs, hashtags, mentions, emails, numbers, custom DNT terms,
    and handles glossary terms to prevent neural translation corruption.
    """

    # Regex patterns
    URL_REGEX = re.compile(r"https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_+.~#?&/=]*|www\.[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_+.~#?&/=]*", re.IGNORECASE)
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
    MENTION_REGEX = re.compile(r"(?<!\w)@[A-Za-z0-9_]{2,30}\b")
    HASHTAG_REGEX = re.compile(r"(?<!\w)#[A-Za-z0-9_\u0900-\u0DFF]{2,50}\b")
    # Number with optional currency symbol and unit
    NUMBER_REGEX = re.compile(r"(?:[\$€₹£¥]\s*)?\b\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s*(?:%|kg|km|g|ml|l|cm|m|MB|GB|TB|k|M|B|hrs|mins|sec))?\b")

    def __init__(self, placeholder_prefix: str = "__ENT_"):
        self.prefix = placeholder_prefix

    def mask(
        self,
        text: str,
        do_not_translate: Optional[List[str]] = None,
        glossary: Optional[Dict[str, str]] = None,
    ) -> MaskResult:
        """
        Scan text, identify all protected elements, and substitute with deterministic placeholders.
        """
        if not text:
            return MaskResult(masked_text="", items=[])

        do_not_translate = do_not_translate or []
        glossary = glossary or {}

        # Collect matches as (start, end, category, original_val, replacement_val)
        matches: List[Tuple[int, int, str, str, str]] = []

        # 1. Custom Do-Not-Translate terms (highest priority)
        for dnt in do_not_translate:
            if not dnt or not dnt.strip():
                continue
            pattern = re.compile(r"\b" + re.escape(dnt.strip()) + r"\b", re.IGNORECASE)
            for m in pattern.finditer(text):
                matches.append((m.start(), m.end(), "dnt", m.group(), m.group()))

        # 2. Glossary terms (force replacement in target or restore target value)
        glossary_applied = {}
        for source_term, target_term in glossary.items():
            if not source_term or not source_term.strip():
                continue
            pattern = re.compile(r"\b" + re.escape(source_term.strip()) + r"\b", re.IGNORECASE)
            for m in pattern.finditer(text):
                matches.append((m.start(), m.end(), "glossary", m.group(), target_term))
                glossary_applied[source_term] = target_term

        # 3. URLs
        for m in self.URL_REGEX.finditer(text):
            matches.append((m.start(), m.end(), "url", m.group(), m.group()))

        # 4. Emails
        for m in self.EMAIL_REGEX.finditer(text):
            matches.append((m.start(), m.end(), "email", m.group(), m.group()))

        # 5. Mentions (@creator)
        for m in self.MENTION_REGEX.finditer(text):
            matches.append((m.start(), m.end(), "mention", m.group(), m.group()))

        # 6. Hashtags (#trending)
        for m in self.HASHTAG_REGEX.finditer(text):
            matches.append((m.start(), m.end(), "hashtag", m.group(), m.group()))

        # 7. Numbers, currencies, metrics
        for m in self.NUMBER_REGEX.finditer(text):
            matches.append((m.start(), m.end(), "number", m.group(), m.group()))

        # Sort matches by start position ascending, then length descending
        matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))

        # Filter overlapping matches (greedy non-overlapping)
        filtered_matches: List[Tuple[int, int, str, str, str]] = []
        last_end = 0
        for start, end, cat, orig, repl in matches:
            if start >= last_end:
                filtered_matches.append((start, end, cat, orig, repl))
                last_end = end

        # Construct masked string and MaskItem records
        items: List[MaskItem] = []
        masked_parts = []
        curr = 0

        for idx, (start, end, cat, orig, repl) in enumerate(filtered_matches):
            masked_parts.append(text[curr:start])
            placeholder = f"{self.prefix}{idx}__"
            items.append(
                MaskItem(
                    placeholder=placeholder,
                    original_value=orig,
                    replacement_value=repl,
                    category=cat,
                    start_pos=start,
                    end_pos=end,
                )
            )
            masked_parts.append(placeholder)
            curr = end
        masked_parts.append(text[curr:])

        masked_text = "".join(masked_parts)
        return MaskResult(
            masked_text=masked_text,
            items=items,
            glossary_applied=glossary_applied,
        )

    def unmask(self, translated_text: str, mask_result: MaskResult) -> UnmaskResult:
        """
        Restore placeholders with their respective replacement values and validate preservation.
        Handles variations where models insert spaces like '__ ENT_0 __'.
        """
        if not mask_result.items:
            return UnmaskResult(
                unmasked_text=translated_text,
                preserved_entities=[],
                missing_entities=[],
                preservation_ratio=1.0,
                warnings=[],
            )

        result_text = translated_text
        preserved: List[str] = []
        missing: List[str] = []
        warnings: List[str] = []

        for item in mask_result.items:
            # Build regex to match placeholder with potential spacing inserted by tokenizers
            raw_id = item.placeholder.strip("_")
            flexible_regex = re.compile(
                r"_{1,3}\s*" + re.escape(raw_id) + r"\s*_{1,3}",
                re.IGNORECASE,
            )

            if flexible_regex.search(result_text):
                result_text = flexible_regex.sub(item.replacement_value, result_text, count=1)
                preserved.append(item.original_value)
            else:
                # Placeholder was lost or translated
                missing.append(item.original_value)
                warnings.append(
                    f"Entity '{item.original_value}' ({item.category}) placeholder '{item.placeholder}' was missing from output"
                )

        total_entities = len(mask_result.items)
        ratio = len(preserved) / total_entities if total_entities > 0 else 1.0

        return UnmaskResult(
            unmasked_text=result_text,
            preserved_entities=preserved,
            missing_entities=missing,
            preservation_ratio=ratio,
            warnings=warnings,
        )
