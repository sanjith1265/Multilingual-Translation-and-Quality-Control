from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from incubrix.api.app import app

client = TestClient(app)


def test_api_health():
    res = client.get("/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "en" in data["supported_languages"]
    assert "hi" in data["supported_languages"]


def test_api_languages():
    res = client.get("/v1/languages")
    assert res.status_code == 200
    data = res.json()
    assert len(data["supported_languages"]) == 11


def test_api_translate_single():
    payload = {
        "source_text": "Hello world from @incubrix!",
        "source_lang": "en",
        "target_lang": "es",
        "route_override": "mock",
        "enable_qc": True,
    }
    res = client.post("/v1/translate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "@incubrix" in data["translated_text"]
    assert data["route_metadata"]["model_family"] == "Mock"
    assert "review_status" in data


def test_api_batch_translate():
    payload = {
        "batch_id": "test-api-batch",
        "segments": [
            {"id": "s1", "text": "Welcome to our video!"},
            {"id": "s2", "text": "Subscribe for more updates at https://incubrix.com"}
        ],
        "source_lang": "en",
        "target_lang": "hi",
        "enable_qc": False,
        "enable_cache": True,
    }
    res = client.post("/v1/batch", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["total_segments"] == 2
    assert data["completed_segments"] == 2


def test_api_review_queue():
    res = client.get("/v1/review-queue")
    assert res.status_code == 200
    assert "total_flagged" in res.json()
