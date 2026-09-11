from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from incubrix.core.schema import ReviewQueueItem


class ReviewQueueManager:
    """
    Manages the review_queue.json artifact.
    Gathers low-confidence or anomalous translations into an actionable queue for human review.
    """

    def __init__(self, queue_file: str = "d:/incubrix/data/review_queue.json"):
        self.queue_file = Path(queue_file)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.queue_file.exists():
            self._write_items([])

    def _read_items(self) -> List[Dict[str, Any]]:
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_items(self, items: List[Dict[str, Any]]) -> None:
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)

    def add_item(
        self,
        segment_id: str,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        model_used: str,
        qc_flags: List[str],
        suggested_action: str = "Manual review required due to QC failure",
    ) -> ReviewQueueItem:
        items = self._read_items()

        item = ReviewQueueItem(
            review_id=str(uuid.uuid4())[:8],
            segment_id=segment_id,
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            model_used=model_used,
            qc_flags=qc_flags,
            suggested_action=suggested_action,
            created_at=datetime.utcnow().isoformat(),
        )

        items.append(item.model_dump())
        self._write_items(items)
        return item

    def get_all(self) -> List[Dict[str, Any]]:
        return self._read_items()

    def clear(self) -> None:
        self._write_items([])
