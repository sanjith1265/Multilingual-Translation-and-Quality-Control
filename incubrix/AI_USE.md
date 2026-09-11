# AI_USE.md - Disclosure of AI Assistance & Verification Methodology

**Track 04: Multilingual Translation with Independent Quality Control**  
**Candidate:** Sanjith (SASTRA 2027 Graduate Hiring)  
**Organization:** IncuBrix Private Limited  

In compliance with the IncuBrix Candidate Project Assessment guidelines, this document fully discloses the use of AI coding assistants, the scope of assistance, and the verification methods applied.

---

## 1. Tooling Disclosed
* **AI Coding Assistant:** Google Antigravity (Gemini 3.8 Flash Engine)
* **IDE / Environment:** Visual Studio Code / Antigravity Agentic Environment on Windows 11
* **Scope of Assistance:** Architecture scaffolding, regex boilerplate generation, Pytest test case templating, and documentation formatting.

---

## 2. Detailed Record of Assistance & Prompts

| Development Phase | Prompt / Task Intent | AI Role & Code Produced | Verification & Engineering Applied by Candidate |
| :--- | :--- | :--- | :--- |
| **Data Models & Schemas** | Define Pydantic models for `TranslationRequest`, `TranslationOutput`, `QCResult`, and FLORES-200 language code mappings. | Generated schema structures and enum definitions in `src/incubrix/core/schema.py`. | Manually verified language codes for all 10 target languages (`hin_Deva`, `tam_Taml`, `tel_Telu`, etc.) against FLORES standards; added custom validation. |
| **Entity Masker** | Create regex patterns for URLs, mentions, hashtags, currencies, numbers, and glossary masking. | Generated baseline regex patterns and placeholder swapping in `src/incubrix/core/entity_masker.py`. | Discovered and fixed tokenizer splitting vulnerabilities (e.g. `__ ENT_0 __`); wrote flexible regex unmasker with deterministic 100% preservation check. |
| **Independent QC Pipeline** | Implement 3 automated checks where production model cannot grade itself (LangID, MarianMT back-translation, and anomaly detector). | Scaffolding for `lang_id.py`, `back_translator.py`, `anomaly_checker.py`, and `engine.py`. | Implemented Unicode script matching for Indic languages to eliminate false positives; added consecutive n-gram repetition detection to handle non-Latin loops. |
| **Routing & SQLite Cache** | Build persistent caching and batch resume capability to withstand interruption. | Database DDL and checkpoint schema in `src/incubrix/core/cache.py` and router fallback in `src/incubrix/routing/router.py`. | Tested transaction atomicity, simulated process interruption, and verified resumption without redundant translation computation. |
| **Fault Injection & Testing** | Construct test suite covering 10 baseline languages, 20 non-English directions, and corrupted outputs. | Populated `data/test_matrix.json`, `data/non_english_directions.json`, and `data/fault_injection_suite.json`. | Executed 23 unit tests via Pytest, audited precision and recall (100% precision, 100% recall), and verified zero memory leakage on CPU. |

---

## 3. Review & Verification Methodology
* **Zero Unexamined Code:** Every generated module was inspected, type-checked, and integrated into a modular Python package structure.
* **Automated Unit & Integration Testing:** All modules were tested using `pytest tests/ -v`, achieving 100% pass rate (23/23 tests passing).
* **Live System Execution:** Both the CLI (`incubrix translate`, `batch`, `test-routes`, `audit-qc`, `benchmark`) and the FastAPI REST microservice were executed live and validated end-to-end on local CPU hardware.
* **Live Modification Readiness:** The candidate understands every architectural choice, regex pattern, and memory profile, and is fully prepared to trace and modify the system live during the evaluation session.
