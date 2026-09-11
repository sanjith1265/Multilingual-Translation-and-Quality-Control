from __future__ import annotations
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List


class TranslationCache:
    """
    SQLite-backed cache and batch resume manager.
    Guarantees deterministic caching and allows interrupted batch translations
    to resume without re-computing already translated segments.
    """

    def __init__(self, db_path: str = "d:/incubrix/data/translation_cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Segment-level translation cache
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS segment_cache (
                    cache_key TEXT PRIMARY KEY,
                    source_hash TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # Batch checkpoint table for resume capability
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS batch_checkpoints (
                    batch_id TEXT NOT NULL,
                    segment_id TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (batch_id, segment_id)
                )
                """
            )
            conn.commit()

    @staticmethod
    def compute_key(source_text: str, source_lang: str, target_lang: str, model_id: str) -> str:
        payload = f"{source_lang}|{target_lang}|{model_id}|{source_text.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_segment(
        self, source_text: str, source_lang: str, target_lang: str, model_id: str
    ) -> Optional[Dict[str, Any]]:
        key = self.compute_key(source_text, source_lang, target_lang, model_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT output_json FROM segment_cache WHERE cache_key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["output_json"])
        return None

    def set_segment(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        model_id: str,
        output_dict: Dict[str, Any],
    ) -> None:
        key = self.compute_key(source_text, source_lang, target_lang, model_id)
        source_hash = hashlib.md5(source_text.encode("utf-8")).hexdigest()
        translated_text = output_dict.get("translated_text", "")
        output_json = json.dumps(output_dict, ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO segment_cache 
                (cache_key, source_hash, source_lang, target_lang, model_id, source_text, translated_text, output_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (key, source_hash, source_lang, target_lang, model_id, source_text, translated_text, output_json),
            )
            conn.commit()

    def record_batch_checkpoint(self, batch_id: str, segment_id: str, output_dict: Dict[str, Any]) -> None:
        """Save progress for an in-flight batch job."""
        output_json = json.dumps(output_dict, ensure_ascii=False)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO batch_checkpoints (batch_id, segment_id, output_json)
                VALUES (?, ?, ?)
                """,
                (batch_id, segment_id, output_json),
            )
            conn.commit()

    def get_batch_completed_segments(self, batch_id: str) -> Dict[str, Dict[str, Any]]:
        """Retrieve all segments completed so far for an interrupted batch."""
        completed = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT segment_id, output_json FROM batch_checkpoints WHERE batch_id = ?", (batch_id,))
            for row in cursor.fetchall():
                completed[row["segment_id"]] = json.loads(row["output_json"])
        return completed

    def clear_batch(self, batch_id: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM batch_checkpoints WHERE batch_id = ?", (batch_id,))
            conn.commit()
