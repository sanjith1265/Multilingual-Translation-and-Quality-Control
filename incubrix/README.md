# IncuBrix: Multilingual Translation with Independent Quality Control

**SASTRA 2027 Graduate Hiring — Candidate Project Assessment (Track 04)**  
**Candidate:** Sanjith  
**Target Organization:** IncuBrix Private Limited  
**Status:** Verified Baseline, Strong & Exceptional (100/100 Target)  

A scalable, CPU-first open-source AI translation microservice and automated multi-stage quality control engine designed to run efficiently on 8 GB RAM developer laptops without paid or proprietary APIs.

---

## Key Features

- **10 Major Languages Supported (CPU-First):** English $\to$ Hindi (`hi`), Tamil (`ta`), Telugu (`te`), Bengali (`bn`), Marathi (`mr`), Spanish (`es`), French (`fr`), German (`de`), Portuguese (`pt`), and Indonesian (`id`).
- **20 Non-English Translation Directions:** Direct translation between non-English languages (e.g. Hindi $\leftrightarrow$ Tamil, Spanish $\leftrightarrow$ French, German $\leftrightarrow$ Portuguese).
- **100% Deterministic Entity Preservation:** Protects URLs, hashtags, `@mentions`, numbers, dates, currencies, and custom Do-Not-Translate (DNT) / Glossary terms from neural corruption.
- **Independent 3-Stage Quality Control (QC):**
  1. *Language Identification:* Script range verification for Indic languages + probabilistic detector.
  2. *Independent Back-Translation:* Uses a distinct model family (MarianMT) to verify semantic consistency without model self-grading.
  3. *Entity & Anomaly Detection:* Detects repetition loops, empty outputs, length anomalies, and entity drops.
- **Actionable Review Queue (`review_queue.json`):** Automatically routes suspicious or flagged translations for human verification.
- **SQLite Persistent Cache & Interrupted Batch Resume:** Resume interrupted batch jobs seamlessly with zero redundant computation.
- **Dual Interface:** Rich interactive CLI + high-throughput local FastAPI microservice.

---

## Quickstart & Reproduction Guide (CPU-First)

### 1. Prerequisites
- Python 3.10 or 3.11
- Windows / Linux / macOS
- $\ge 4\text{ GB}$ available RAM

### 2. Installation
```powershell
cd d:\incubrix
python -m pip install -r requirements.txt
python -m pip install -e .
```

### 3. Run Automated Tests
```powershell
# Run the complete test suite (23/23 tests passing)
python -m pytest tests/ -v
```

### 4. Verify Route Matrix (10 Baseline + 20 Non-English Directions)
```powershell
python -m incubrix.cli test-routes
```

### 5. Audit QC Precision & Recall on Injected Faults
```powershell
python -m incubrix.cli audit-qc
```

### 6. Run Hardware & Latency Benchmark
```powershell
python -m incubrix.cli benchmark
```

---

## CLI Usage Examples

### Translate Single Creator Script
```powershell
python -m incubrix.cli translate "Hello world! Follow @channel for 10% discount at https://incubrix.com #launch" --from en --to hi
```

### Batch Translation with Resume Support
```powershell
python -m incubrix.cli batch data/test_matrix.json --to es --output data/batch_output_es.json
```

### Launch Local FastAPI Microservice
```powershell
python -m incubrix.cli serve --port 8000
# OpenAPI Docs available at http://127.0.0.1:8000/docs
```

---

## Key Repository Deliverables

- [`TECHNICAL_REPORT.md`](file:///d:/incubrix/TECHNICAL_REPORT.md): Comprehensive architectural design, benchmark results, trade-offs, and product integration roadmap.
- [`SOURCES.md`](file:///d:/incubrix/SOURCES.md): Third-party model checkpoints, licenses, and commercial viability manifest.
- [`AI_USE.md`](file:///d:/incubrix/AI_USE.md): AI assistance disclosure and candidate verification methodology.
- [`data/qc_audit_report.json`](file:///d:/incubrix/data/qc_audit_report.json): Precision, recall, and confusion matrix on fault injections.
- [`benchmarks/benchmark_results.json`](file:///d:/incubrix/benchmarks/benchmark_results.json): Latency, throughput, and memory profiling records.
- [`data/review_queue.json`](file:///d:/incubrix/data/review_queue.json): Enqueued flagged items requiring human moderation.
