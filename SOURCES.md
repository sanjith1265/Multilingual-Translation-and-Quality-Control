# SOURCES.md - Third-Party Code, Models, and License Manifest

**Track 04: Multilingual Translation with Independent Quality Control**  
**Candidate:** Sanjith (SASTRA 2027 Graduate Hiring)  
**Organization:** IncuBrix Private Limited  

This document inventories every third-party model, library, weight checkpoint, and dataset utilized in the IncuBrix translation and independent QC platform, detailing licenses, commercial viability, and attribution obligations.

---

## 1. Machine Learning Models & Weights

| Asset / Checkpoint | Version / Commit | Provider / Author | Role in System | Code License | Weights License | Commercial Use Status | Attribution Obligation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NLLB-200-Distilled-600M** | `facebook/nllb-200-distilled-600M` | Meta AI | Primary multi-directional translation engine (covers 10 target languages + English) | MIT | CC-BY-NC 4.0 (Research/Baseline) / OpenWeights | Approved for internal benchmarking & evaluation; production commercial migration paths to CTranslate2 INT8 | Cite NLLB Team (2022) |
| **MarianMT (Opus-MT)** | `Helsinki-NLP/opus-mt-*` | University of Helsinki (Tiedemann & Thottingal) | Secondary comparison model & Independent Back-Translation QC check | Apache 2.0 | CC-BY-4.0 | Fully Commercially Reusable | Cite Tiedemann (EAMT 2020) |
| **CTranslate2** | `4.8.2` | OpenNMT Team | High-performance CPU inference engine with INT8 dynamic quantization | MIT | MIT | Fully Commercially Reusable | Include MIT copyright notice |

---

## 2. Core Python Libraries

| Library | Version | Role in Architecture | License | Commercial Permissibility |
| :--- | :--- | :--- | :--- | :--- |
| **Transformers** | `>=4.40.0` | Tokenization and Seq2Seq execution | Apache 2.0 | Permissive commercial use |
| **PyTorch** | `>=2.2.0` | Deep learning CPU runtime & tensor ops | BSD-3-Clause | Permissive commercial use |
| **SentencePiece** | `>=0.2.0` | Subword tokenization for Marian & NLLB | Apache 2.0 | Permissive commercial use |
| **SacreBLEU** | `>=2.4.0` | Standardized reference metric calculation (BLEU, chrF) | Apache 2.0 | Permissive commercial use |
| **LangDetect** | `>=1.0.9` | QC Check 1: Probabilistic n-gram language detector | Apache 2.0 | Permissive commercial use |
| **FastAPI** | `>=0.110.0` | High-throughput local REST microservice API | MIT | Permissive commercial use |
| **Uvicorn** | `>=0.29.0` | ASGI production web server | BSD-3-Clause | Permissive commercial use |
| **Pydantic** | `>=2.7.0` | Data schema validation & serialization | MIT | Permissive commercial use |
| **Rich & Click** | `>=13.7.0`, `>=8.1.7`| CLI interface, tables, and progress bars | MIT | Permissive commercial use |
| **PSUtil** | `>=5.9.0` | Real-time CPU & RSS RAM memory tracking | BSD-3-Clause | Permissive commercial use |
| **OpenPyXL** | `>=3.1.2` | Official workbook evaluation interaction | MIT | Permissive commercial use |

---

## 3. Commercial Reusability Analysis & Product Recommendation

### Recommended Commercial Stack:
1. **European & High-Volume Directional Pairs:** Deploy **MarianMT (CC-BY-4.0 / Apache 2.0)** converted to **CTranslate2 INT8**. This provides ultra-low latency ($< 15\text{ ms}$ on CPU), negligible RAM ($< 350\text{ MB}$), and zero commercial restrictions.
2. **Multilingual & Indic Pairs:** For Indian regional languages (Hindi, Tamil, Telugu, Bengali, Marathi), deploy quantized **IndicTrans2** (AI4Bharat, MIT license) or commercially licensed distilled NLLB models.
3. **Independent QC Pipeline:** The 3-stage QC architecture (Unicode script analysis + LangDetect + Independent MarianMT back-translation + Deterministic entity regex) uses 100% commercially permissive components (Apache 2.0 & MIT), enabling IncuBrix to audit third-party translations in production without licensing exposure.
