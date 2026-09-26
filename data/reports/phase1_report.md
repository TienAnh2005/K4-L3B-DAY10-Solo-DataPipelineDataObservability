# Phase 1: Baseline Pipeline & Data Observability Report

> **Generated at:** Current Run  
> **Source:** Crossref REST API  
> **Query:** `agentic retrieval augmented generation large language model`

---

## 1. Executive Summary

This report establishes the baseline performance and data quality health of the scholarly RAG pipeline before any data corruption. Dữ liệu thô từ Crossref API được làm sạch, kiểm định qua Great Expectations 1.x, đánh giá độ tươi mới (Freshness SLA) và index vào ChromaDB vector store.

- **Raw Records Ingested:** 24
- **Cleaned Documents:** 24
- **Quality Gate (GX 1.x):** ✅ PASSED
- **Freshness SLA:** ✅ HEALTHY
- **Retrieval Hit Rate:** 100.00%
- **Mean Token F1:** 1.0000

---

## 2. Data Observability & Quality Assurance

### 2.1 Great Expectations 1.x Quality Gate
- **Status:** `SUCCESS`
- **Total Records Validated:** 24
- **Expectation Details:**
  - ✅ `expect_table_row_count_to_be_between`: kwargs={'batch_id': 'papers_source_baseline-papers_asset', 'min_value': 15, 'max_value': 30}
  - ✅ `expect_column_values_to_not_be_null`: kwargs={'batch_id': 'papers_source_baseline-papers_asset', 'column': 'paper_id'}
  - ✅ `expect_column_values_to_be_unique`: kwargs={'batch_id': 'papers_source_baseline-papers_asset', 'column': 'paper_id'}
  - ✅ `expect_column_values_to_not_be_null`: kwargs={'batch_id': 'papers_source_baseline-papers_asset', 'column': 'title'}
  - ✅ `expect_column_value_lengths_to_be_between`: kwargs={'batch_id': 'papers_source_baseline-papers_asset', 'column': 'title', 'min_value': 8}
  - ✅ `expect_column_value_lengths_to_be_between`: kwargs={'batch_id': 'papers_source_baseline-papers_asset', 'column': 'summary', 'min_value': 15}

### 2.2 Freshness SLA (Threshold: 180 days)
- **Total Records:** 24
- **Stale Records (> 180 days):** 1 (4.17%)
- **Latest Publication Date:** `2026-07-22`
- **Oldest Publication Date:** `2026-03-28`
- **SLA Compliant:** `YES`

---

## 3. Retrieval & QA Benchmark Metrics

- **Evaluation Test Set Size:** 10 questions
- **Retrieval Hit Rate:** `1.0000`
- **Mean Token F1 Score:** `1.0000`
- **Judge Accuracy:** `1.0000`
- **Mean Judge Score (1-5):** `5.00`

---
*Report generated automatically by Data Pipeline Observability Framework.*
